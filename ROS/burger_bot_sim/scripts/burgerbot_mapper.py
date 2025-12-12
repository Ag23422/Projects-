#!/usr/bin/env python3
import rospy
import json
import os
import random
import math
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

class BurgerBotMapper:
    def __init__(self):
        rospy.init_node("burgerbot_mapper")

        self.pub = rospy.Publisher("/cmd_vel", Twist, queue_size=10)
        rospy.Subscriber("/odom", Odometry, self.odom_callback)
        rospy.Subscriber("/scan", LaserScan, self.lidar_callback)

        self.current_pose = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.lidar_data = []
        self.last_logged = (0.0, 0.0)

        self.log_path = os.path.expanduser("~/burgerbot_log.json")
        self.logs = []
        self.rate = rospy.Rate(10)

        rospy.loginfo("🍔 BurgerBot Mapper started")
        self.move_and_log()

    def odom_callback(self, msg):
        pos = msg.pose.pose.position
        self.current_pose = {"x": pos.x, "y": pos.y, "z": pos.z}

    def lidar_callback(self, msg):
        self.lidar_data = list(msg.ranges)

    def distance_moved(self):
        dx = self.current_pose["x"] - self.last_logged[0]
        dy = self.current_pose["y"] - self.last_logged[1]
        return math.sqrt(dx*dx + dy*dy)

    def log_data(self):
        data = {
            "x": self.current_pose["x"],
            "y": self.current_pose["y"],
            "z": self.current_pose["z"],
            "lidar_min": min(self.lidar_data) if self.lidar_data else None,
            "lidar_max": max(self.lidar_data) if self.lidar_data else None,
            "lidar_points": len(self.lidar_data),
            "time": rospy.get_time()
        }
        self.logs.append(data)
        with open(self.log_path, "w") as f:
            json.dump(self.logs, f, indent=2)
        rospy.loginfo(f"📍 Logged data point: {data}")
        self.last_logged = (self.current_pose["x"], self.current_pose["y"])

    def move_random_direction(self):
        twist = Twist()
        twist.linear.x = 0.2
        twist.angular.z = random.uniform(-1.0, 1.0)
        for _ in range(20):  # move for ~2 seconds
            self.pub.publish(twist)
            self.rate.sleep()
        twist.linear.x = 0
        twist.angular.z = 0
        self.pub.publish(twist)

    def move_and_log(self):
        while not rospy.is_shutdown():
            if self.distance_moved() >= 1.0:
                self.log_data()
                self.move_random_direction()
            else:
                self.pub.publish(Twist())
            self.rate.sleep()

if __name__ == "__main__":
    try:
        BurgerBotMapper()
    except rospy.ROSInterruptException:
        pass
