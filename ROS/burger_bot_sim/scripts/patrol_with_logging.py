#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math
import json
import os

class TurtleBotMapper:
    def __init__(self):
        rospy.init_node('turtlebot_mapper', anonymous=True)
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
                self.last_logged_distance = 0.0
                continue

            elif not self.forward and dist <= self.left_bound:
                rospy.loginfo("⬅️ Reached left bound, turning forward...")
                self.turn_around()
                self.forward = True
                self.last_logged_distance = 0.0
                continue

            # Move forward
            twist.linear.x = 0.2 if self.forward else -0.2
            self.pub.publish(twist)

            # Log every 1 meter
            distance_since_last = abs(dist - self.last_logged_distance)
            if distance_since_last >= 1.0:
                rospy.loginfo(f"📍 Logging data at x={self.current_pose['x']:.2f}")
                self.log_data(self.current_pose)
                self.last_logged_distance = dist

            self.rate.sleep()

    def log_data(self, pose):
        with open(self.json_file, "r") as f:
            data = json.load(f)

        record = {
            "position": {
                "x": pose["x"],
                "y": pose["y"],
                "z": pose["z"]
            },
            "orientation": pose["orientation"],
            "timestamp": rospy.Time.now().to_sec()
        }

        data["records"].append(record)

        with open(self.json_file, "w") as f:
            json.dump(data, f, indent=4)

        rospy.loginfo("📝 Position logged successfully.")

    def turn_around(self):
        twist = Twist()
        twist.linear.x = 0
        twist.angular.z = 0.6

        start_time = rospy.Time.now().to_sec()
        while rospy.Time.now().to_sec() - start_time < 3.0:
            self.pub.publish(twist)
            self.rate.sleep()

        twist.angular.z = 0
        self.pub.publish(twist)

if __name__ == "__main__":
    try:
        bot = TurtleBotMapper()
        bot.move_and_log()
    except rospy.ROSInterruptException:
        pass
