#!/usr/bin/env python3
import rospy, json, random, os
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

data_log = []

def odom_callback(msg):
    """Collect position + orientation."""
    pos = msg.pose.pose.position
    ori = msg.pose.pose.orientation
    (roll, pitch, yaw) = euler_from_quaternion([ori.x, ori.y, ori.z, ori.w])
    data_log.append({
        "x": round(pos.x, 3),
        "y": round(pos.y, 3),
        "z": round(pos.z, 3),
        "yaw_deg": round(yaw * 180 / 3.14159, 2),
        "timestamp": rospy.get_time()
    })

def random_move(pub):
    """Move forward 1 m, then rotate random heading."""
    twist = Twist()
    twist.linear.x = 0.2
    t0 = rospy.Time.now().to_sec()
    while rospy.Time.now().to_sec() - t0 < 5:   # move ~1 m
        pub.publish(twist)
        rospy.sleep(0.1)
    twist.linear.x = 0
    pub.publish(twist)

    # Random rotate
    turn = random.choice([-1, 1])
    twist.angular.z = 0.6 * turn
    t1 = rospy.Time.now().to_sec()
    while rospy.Time.now().to_sec() - t1 < random.uniform(1.5, 3.0):
        pub.publish(twist)
        rospy.sleep(0.1)
    twist.angular.z = 0
    pub.publish(twist)

def main():
    rospy.init_node('burgerbot_random_mapper')
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
    rospy.Subscriber('/odom', Odometry, odom_callback)
    rospy.sleep(2)

    rate = rospy.Rate(0.05)  # one cycle every 20 s
    while not rospy.is_shutdown():
        random_move(pub)
        rate.sleep()

    path = os.path.join(os.getenv('HOME'), 'burgerbot_map_log.json')
    with open(path, 'w') as f:
        json.dump(data_log, f, indent=2)
    rospy.loginfo(f"Map log saved to {path}")

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
