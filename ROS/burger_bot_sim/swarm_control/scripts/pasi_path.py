#!/usr/bin/env python3
import rospy
import math
from geometry_msgs.msg import PoseStamped

def circular_path():
    rospy.init_node("circular_path_node")

    # Publisher to local setpoint position
    pub = rospy.Publisher("/mavros/setpoint_position/local", PoseStamped, queue_size=10)

    rate = rospy.Rate(20)  # 20 Hz publish rate

    # Circle parameters
    radius = 5.0       # meters
    altitude = 3.0     # meters
    center_x = 0.0
    center_y = 0.0
    angular_speed = 0.3  # rad/s

    msg = PoseStamped()
    msg.header.frame_id = "map"

    start_time = rospy.Time.now().to_sec()

    while not rospy.is_shutdown():
        t = rospy.Time.now().to_sec() - start_time
        theta = angular_speed * t

        x = center_x + radius * math.cos(theta)
        y = center_y + radius * math.sin(theta)
        z = altitude

        msg.header.stamp = rospy.Time.now()
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z

        # yaw fixed forward
        msg.pose.orientation.w = 1.0

        pub.publish(msg)
        rate.sleep()

if __name__ == "__main__":
    try:
        circular_path()
    except rospy.ROSInterruptException:
        pass
