#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math
import json
import os

class TurtleBotMapper:
    def __init__(self):
        rospy.init_node('move_turtlebot', anonymous=True)
        self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)

        self.rate = rospy.Rate(10)
        self.current_pose = None
        self.start_pose = None
        self.last_logged_distance = 0.0

        # Movement bounds (adjust to your world)
        self.left_bound = 0.0
        self.right_bound = 2.5
        self.forward = True

        # File for JSON logs
        self.log_path = os.path.expanduser("~/catkin_ws/src/burger_bot_sim/logs")
        os.makedirs(self.log_path, exist_ok=True)
        self.json_file = os.path.join(self.log_path, "turtlebot_map.json")

        # Initialize log file
        with open(self.json_file, "w") as f:
            json.dump({"records": []}, f, indent=4)

        rospy.loginfo("✅ TurtleBot Mapper initialized.")

    def odom_callback(self, msg):
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        self.current_pose = {
            "x": pos.x,
            "y": pos.y,
            "z": pos.z,
            "orientation": {
                "x": ori.x,
                "y": ori.y,
                "z": ori.z,
                "w": ori.w
            }
        }
        if self.start_pose is None:
            self.start_pose = pos.x

    def move_and_log(self):
        twist = Twist()
        while not rospy.is_shutdown():
            if self.current_pose is None:
                rospy.loginfo("⏳ Waiting for odometry...")
                self.rate.sleep()
                continue

            # Current distance traveled relative to start
            dist = self.current_pose["x"] - self.start_pose

            # Check bounds
            if self.forward and dist >= self.right_bound:
                rospy.loginfo("➡️ Reached right bound, turning back...")
                self.turn_around()
                self.forward = False
                self.last_logged_dist
