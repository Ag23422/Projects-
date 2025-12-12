#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import tf
import random, math, json, time, os

class BurgerBotGazebo:
    def __init__(self):
        rospy.init_node('burgerbot_gazebo_mapper', anonymous=True)
        self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        self.rate = rospy.Rate(10)

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.yaw = 0.0

        self.map_data = []
        self.steps = 10
        self.step_distance = 1.0

        rospy.loginfo("BurgerBot Mapper Initialized")

    def odom_callback(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.z = msg.pose.pose.position.z

        orientation_q = msg.pose.pose.orientation
        orientation_list = [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w]
        (_, _, yaw) = tf.transformations.euler_from_quaternion(orientation_list)
        self.yaw = yaw

    def move_forward(self, distance=1.0):
        twist = Twist()
        speed = 0.2
        duration = distance / speed
        rospy.loginfo(f"Moving forward {distance} m")

        t0 = rospy.Time.now().to_sec()
        while (rospy.Time.now().to_sec() - t0) < duration:
            twist.linear.x = speed
            self.pub.publish(twist)
            self.rate.sleep()
        twist.linear.x = 0
        self.pub.publish(twist)

    def random_turn(self):
        twist = Twist()
        ang = random.choice([-90, -45, 45, 90])
        rospy.loginfo(f"Turning {ang}°")
        angular_speed = 0.5
        duration = abs(math.radians(ang)) / angular_speed
        direction = 1 if ang > 0 else -1

        t0 = rospy.Time.now().to_sec()
        while (rospy.Time.now().to_sec() - t0) < duration:
            twist.angular.z = direction * angular_speed
            self.pub.publish(twist)
            self.rate.sleep()
        twist.angular.z = 0
        self.pub.publish(twist)

    def read_environment(self):
        return {
            "temperature": round(random.uniform(20, 30), 1),
            "humidity": round(random.uniform(30, 70), 1),
            "light": round(random.uniform(100, 900), 1),
            "battery": round(random.uniform(3.6, 4.2), 2)
        }

    def log_point(self):
        env = self.read_environment()
        record = {
            "position": {"x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3)},
            "heading_deg": round(math.degrees(self.yaw) % 360, 2),
            "environment": env,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.map_data.append(record)
        rospy.loginfo(f"Logged data at x={record['position']['x']} y={record['position']['y']}")

    def save_json(self):
        path = os.path.expanduser("~/catkin_ws/src/burgerbot_sim/burgerbot_map.json")
        with open(path, "w") as f:
            json.dump(self.map_data, f, indent=4)
        rospy.loginfo(f"Saved map data to {path}")

    def run(self):
        rospy.sleep(2)
        for i in range(self.steps):
            rospy.loginfo(f"--- Step {i+1}/{self.steps} ---")
            self.random_turn()
            self.move_forward(self.step_distance)
            self.log_point()
        self.save_json()
        rospy.loginfo("Mapping complete!")


if __name__ == "__main__":
    bot = BurgerBotGazebo()
    bot.run()
