#!/usr/bin/env python3
import rospy
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState, GetModelState, SpawnModel
from geometry_msgs.msg import Pose
import sys, tty, termios
import threading
import math
import random
import tf.transformations as tft

# ----- Keyboard helper -----
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# ----- ROS Init -----
rospy.init_node('swarm_control_with_base_stations')
rospy.wait_for_service('/gazebo/set_model_state')
set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
rospy.wait_for_service('/gazebo/get_model_state')
get_state = rospy.ServiceProxy('/gazebo/get_model_state', GetModelState)
rospy.wait_for_service('/gazebo/spawn_sdf_model')
spawn_model = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)

rate = rospy.Rate(20)

# ----- Parameters -----
hover_z = 1.0
move_speed = 0.2
yaw_speed = 0.1
min_spacing = 2.0

wall_y_patrol = -2.0
wall_y_support = 4.0
support_altitude = 3.0
num_patrolling = 10
num_support = 3

# Base station positions (behind fence & supports)
landing_x, landing_y = -1.0, -4.0   # red landing marker (no drone)
takeoff_x, takeoff_y =  1.0, -4.0   # green launchpad drone (spawned by script)

# Path to the quadrotor SDF model on your system (adjust if needed)
sdf_model_path = "/home/ansh/.gazebo/models/quadrotor/model.sdf"

# ----- Helper: Spawn colored drone -----
def spawn_colored_drone(name, x, y, z, color):
    base_pose = Pose()
    base_pose.position.x = x
    base_pose.position.y = y
    base_pose.position.z = z

    with open(sdf_model_path, "r") as f:
        sdf_xml = f.read()

    # naive material override (works for many model SDFs)
    sdf_xml = sdf_xml.replace(
        "<material>",
        f"<material><ambient>{color} 1</ambient><diffuse>{color} 1</diffuse>"
    )

    try:
        spawn_model(name, sdf_xml, "", base_pose, "world")
        rospy.loginfo(f"{name} spawned at ({x}, {y}, {z}) color {color}")
    except Exception as e:
        rospy.logwarn(f"{name} spawn failed or already exists: {e}")

# ----- Landing pad marker (red cylinder) -----
landing_pad_sdf = """
<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="landing_pad_marker">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <geometry>
          <cylinder>
            <radius>0.3</radius>
            <length>0.05</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>1 0 0 1</ambient>
          <diffuse>1 0 0 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>
"""

pad_pose = Pose()
pad_pose.position.x = landing_x
pad_pose.position.y = landing_y
pad_pose.position.z = 0.0

try:
    spawn_model("landing_pad_marker", landing_pad_sdf, "", pad_pose, "world")
    rospy.loginfo(f"Landing pad marker spawned at ({landing_x}, {landing_y}, 0)")
except Exception:
    rospy.logwarn("Landing pad marker already exists or failed to spawn")

# ----- Spawn the green launchpad drone (inactive until used) -----
spawn_colored_drone("takeoff_station_drone", takeoff_x, takeoff_y, 0.0, "0 1 0")

# ----- Drone setup -----
drones = {}

# 10 patrol drones from SDF (active at start)
for i in range(1, num_patrolling + 1):
    drones[f'patrol_drone_{i}'] = {'active': True, 'type': 'patrol'}

# the extra green launchpad drone (spawned above) — keep inactive until needed
drones["takeoff_station_drone"] = {'active': False, 'type': 'patrol'}
drones["takeoff_station_drone"]['state'] = ModelState()
drones["takeoff_station_drone"]['state'].model_name = "takeoff_station_drone"
drones["takeoff_station_drone"]['state'].pose.position.x = takeoff_x
drones["takeoff_station_drone"]['state'].pose.position.y = takeoff_y
drones["takeoff_station_drone"]['state'].pose.position.z = 0.0

# support drones from SDF
for i in range(1, num_support + 1):
    drones[f'support_drone_{i}'] = {'active': True, 'type': 'support', 'special_mode': False}

# record initial positions (for reset)
initial_positions = {}
for name in drones.keys():
    try:
        resp = get_state(name, '')
        init_x = resp.pose.position.x
        init_y = resp.pose.position.y
        init_z = resp.pose.position.z
        initial_positions[name] = (init_x, init_y, init_z)
        if 'state' not in drones[name]:
            drones[name]['state'] = ModelState()
            drones[name]['state'].model_name = name
            drones[name]['state'].pose = resp.pose
    except Exception:
        rospy.logwarn(f"Could not read state for {name} (may be the spawned model or missing)")

print("Controls: D = toggle formation, B = handover swap, P = support ascend, M = reset")

# ----- Helpers -----
def safe_position(drone, target_x, target_y):
    # ensure patrol drones stay behind fence
    target_y = min(target_y, wall_y_patrol)
    return target_x, target_y

def is_too_close(drone, x, y):
    for d in drones.values():
        if d['active'] and d.get('type') == 'patrol' and d is not drone:
            dx = x - d['state'].pose.position.x
            dy = y - d['state'].pose.position.y
            if math.sqrt(dx*dx + dy*dy) < min_spacing:
                return True
    return False

def smooth_move(drone, target_x, target_y, target_z=None, ignore_spacing=False):
    # 3D smooth interpolation (x,y,z). honors spacing in XY unless ignore_spacing=True
    if target_z is None:
        target_z = drone['state'].pose.position.z

    target_x, target_y = safe_position(drone, target_x, target_y)
    dx = target_x - drone['state'].pose.position.x
    dy = target_y - drone['state'].pose.position.y
    dz = target_z - drone['state'].pose.position.z

    steps = max(int(max(abs(dx), abs(dy), abs(dz)) / move_speed), 1)
    for _ in range(steps):
        new_x = drone['state'].pose.position.x + dx / steps
        new_y = drone['state'].pose.position.y + dy / steps
        new_z = drone['state'].pose.position.z + dz / steps
        if ignore_spacing or not is_too_close(drone, new_x, new_y):
            drone['state'].pose.position.x = new_x
            drone['state'].pose.position.y = new_y
            drone['state'].pose.position.z = new_z
            try:
                set_state(drone['state'])
            except Exception as e:
                rospy.logwarn(f"set_state failed for {drone.get('state').model_name if 'state' in drone else 'unknown'}: {e}")
        rate.sleep()

def rotate_towards(drone, target_x, target_y):
    dx = target_x - drone['state'].pose.position.x
    dy = target_y - drone['state'].pose.position.y
    target_yaw = math.atan2(dy, dx)
    q = drone['state'].pose.orientation
    try:
        _, _, current_yaw = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])
    except Exception:
        current_yaw = 0.0
    diff = target_yaw - current_yaw
    steps = max(int(abs(diff)/yaw_speed), 1)
    for i in range(steps):
        new_yaw = current_yaw + diff * (i+1)/steps
        q_new = tft.quaternion_from_euler(0, 0, new_yaw)
        drone['state'].pose.orientation.x = q_new[0]
        drone['state'].pose.orientation.y = q_new[1]
        drone['state'].pose.orientation.z = q_new[2]
        drone['state'].pose.orientation.w = q_new[3]
        try:
            set_state(drone['state'])
        except Exception as e:
            rospy.logwarn(f"set_state rotation failed: {e}")
        rate.sleep()

# ----- Hover loop -----
def hover_loop():
    while not rospy.is_shutdown():
        for d in drones.values():
            if d['active']:
                if d.get('type') == 'support' and d.get('special_mode', False):
                    continue
                # keep them at hover_z when idle (patrol/support)
                d['state'].pose.position.z = hover_z
                try:
                    set_state(d['state'])
                except Exception:
                    pass
        rate.sleep()

threading.Thread(target=hover_loop, daemon=True).start()

# ----- Support random movement -----
def support_random_loop():
    while not rospy.is_shutdown():
        for d in drones.values():
            if d.get('type') == 'support' and d.get('special_mode', False):
                d['state'].pose.position.z = support_altitude
                d['state'].pose.position.x += random.uniform(-0.05, 0.05)
                d['state'].pose.position.y += random.uniform(0.0, 0.05)
                d['state'].pose.position.y = min(d['state'].pose.position.y, wall_y_support)
                try:
                    set_state(d['state'])
                except Exception:
                    pass
        rate.sleep()

threading.Thread(target=support_random_loop, daemon=True).start()

# ----- Keyboard control -----
formation_toggle = None

while not rospy.is_shutdown():
    key = get_key()

    if key.lower() == 'd':
        if formation_toggle is None:
            formation_toggle = 0
        else:
            formation_toggle = 1 - formation_toggle

        active = [d for d in drones.values() if d['active'] and d['type'] == 'patrol']
        n = len(active) if len(active) > 0 else 1
        for idx, d in enumerate(active):
            if formation_toggle == 0:
                # Original circular-ish formation
                angle = (idx / n) * math.pi
                radius = 8.0
                tx = radius * math.cos(angle)
                ty = -3.0 + radius * math.sin(angle)
            elif formation_toggle == 1:
                # Spear formation (straight line along X=0, pointing toward fence)
                spear_spacing = 1.5
                tx = 0.0
                ty = -3.0 - idx * spear_spacing
            tx, ty = safe_position(d, tx, ty)
            rotate_towards(d, tx, ty)
            smooth_move(d, tx, ty, hover_z)

    elif key.lower() == 'b':
        # choose a patrol drone to return (not the green launchpad)
        vacated_slot = None
        leaving_drone = None

        for d in drones.values():
            if d['active'] and d['type'] == 'patrol' and d is not drones["takeoff_station_drone"]:
                # capture the slot immediately (x,y) where the drone currently is (this is the slot we fill)
                vacated_slot = (
                    d['state'].pose.position.x,
                    d['state'].pose.position.y,
                    hover_z
                )
                leaving_drone = d
                break

        if leaving_drone and vacated_slot:
            rospy.loginfo(f"Drone at slot {vacated_slot} will return; launching replacement after landing.")

            def return_and_land(dr, slot):
                rospy.loginfo(f"{dr['state'].model_name} returning to landing pad...")
                rotate_towards(dr, landing_x, landing_y)
                smooth_move(dr, landing_x, landing_y, 0.0, ignore_spacing=True)

                steps = max(int(dr['state'].pose.position.z / move_speed), 1)
                for _ in range(steps):
                    dr['state'].pose.position.z -= hover_z / steps
                    try:
                        set_state(dr['state'])
                    except Exception:
                        pass
                    rate.sleep()
                dr['active'] = False
                rospy.loginfo(f"{dr['state'].model_name} landed on pad and deactivated.")

                replacement = drones["takeoff_station_drone"]
                if not replacement['active']:
                    rospy.loginfo("Preparing replacement drone on green pad...")
                    replacement['active'] = True
                    replacement['state'].pose.position.x = takeoff_x
                    replacement['state'].pose.position.y = takeoff_y
                    replacement['state'].pose.position.z = 0.0
                    try:
                        set_state(replacement['state'])
                    except Exception:
                        pass

                    def takeoff_and_fill(dr2, tgt):
                        rospy.loginfo("Replacement taking off vertically...")
                        steps_up = max(int(hover_z / move_speed), 1)
                        for _ in range(steps_up):
                            dr2['state'].pose.position.z += hover_z / steps_up
                            try:
                                set_state(dr2['state'])
                            except Exception:
                                pass
                            rate.sleep()

                        extra_alt = 1.5
                        rospy.loginfo(f"Ascending to transit altitude ({hover_z + extra_alt}) for safe crossing...")
                        steps_extra = max(int(extra_alt / move_speed), 1)
                        for _ in range(steps_extra):
                            dr2['state'].pose.position.z += extra_alt / steps_extra
                            try:
                                set_state(dr2['state'])
                            except Exception:
                                pass
                            rate.sleep()

                        rospy.loginfo(f"Crossing to target slot {tgt} at high altitude...")
                        smooth_move(dr2, tgt[0], tgt[1], hover_z + extra_alt, ignore_spacing=True)
                        rospy.loginfo("Descending into vacated slot...")
                        smooth_move(dr2, tgt[0], tgt[1], tgt[2], ignore_spacing=True)
                        rospy.loginfo("Replacement filled the slot.")

                    threading.Thread(target=takeoff_and_fill, args=(replacement, slot), daemon=True).start()
                else:
                    rospy.logwarn("Replacement already active; cannot launch another.")

            threading.Thread(target=return_and_land, args=(leaving_drone, vacated_slot), daemon=True).start()

    elif key.lower() == 'p':
        for d in drones.values():
            if d['type'] == 'support':
                d['special_mode'] = True

    elif key.lower() == 'm':
        for name, d in drones.items():
            if name in initial_positions:
                ix, iy, iz = initial_positions[name]
                steps = max(int(abs(d['state'].pose.position.y - iy) / move_speed), 1)
                for _ in range(steps):
                    nx = d['state'].pose.position.x + (ix - d['state'].pose.position.x)/steps
                    ny = d['state'].pose.position.y + (iy - d['state'].pose.position.y)/steps
                    nz = d['state'].pose.position.z + (iz - d['state'].pose.position.z)/steps
                    if not is_too_close(d, nx, ny):
                        d['state'].pose.position.x = nx
                        d['state'].pose.position.y = ny
                        d['state'].pose.position.z = nz
                        try:
                            set_state(d['state'])
                        except Exception:
                            pass
                    rate.sleep()
                d['state'].pose.position.x = ix
                d['state'].pose.position.y = iy
                d['state'].pose.position.z = iz
                try:
                    set_state(d['state'])
                except Exception:
                    pass
                if d['type'] == 'support':
                    d['special_mode'] = False


