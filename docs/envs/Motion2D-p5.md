# prbench/Motion2D-p5-v0
![random action GIF](assets/random_action_gifs/Motion2D-p5.gif)

### Description
A 2D environment where the goal is to reach a target region while avoiding static obstacles.

In this environment, there are always 5 narrow passages.

The robot has a movable circular base and a retractable arm with a rectangular vacuum end effector. The arm and vacuum do not need to be used in this environment.

### Initial State Distribution
![initial state GIF](assets/initial_state_gifs/Motion2D-p5.gif)

### Example Demonstration
![demo GIF](assets/demo_gifs/Motion2D-p5.gif)

### Observation Space
The entries of an array in this Box space correspond to the following object features:
| **Index** | **Object** | **Feature** |
| --- | --- | --- |
| 0 | robot | x |
| 1 | robot | y |
| 2 | robot | theta |
| 3 | robot | base_radius |
| 4 | robot | arm_joint |
| 5 | robot | arm_length |
| 6 | robot | vacuum |
| 7 | robot | gripper_height |
| 8 | robot | gripper_width |
| 9 | target_region | x |
| 10 | target_region | y |
| 11 | target_region | theta |
| 12 | target_region | static |
| 13 | target_region | color_r |
| 14 | target_region | color_g |
| 15 | target_region | color_b |
| 16 | target_region | z_order |
| 17 | target_region | width |
| 18 | target_region | height |
| 19 | obstacle0 | x |
| 20 | obstacle0 | y |
| 21 | obstacle0 | theta |
| 22 | obstacle0 | static |
| 23 | obstacle0 | color_r |
| 24 | obstacle0 | color_g |
| 25 | obstacle0 | color_b |
| 26 | obstacle0 | z_order |
| 27 | obstacle0 | width |
| 28 | obstacle0 | height |
| 29 | obstacle1 | x |
| 30 | obstacle1 | y |
| 31 | obstacle1 | theta |
| 32 | obstacle1 | static |
| 33 | obstacle1 | color_r |
| 34 | obstacle1 | color_g |
| 35 | obstacle1 | color_b |
| 36 | obstacle1 | z_order |
| 37 | obstacle1 | width |
| 38 | obstacle1 | height |
| 39 | obstacle2 | x |
| 40 | obstacle2 | y |
| 41 | obstacle2 | theta |
| 42 | obstacle2 | static |
| 43 | obstacle2 | color_r |
| 44 | obstacle2 | color_g |
| 45 | obstacle2 | color_b |
| 46 | obstacle2 | z_order |
| 47 | obstacle2 | width |
| 48 | obstacle2 | height |
| 49 | obstacle3 | x |
| 50 | obstacle3 | y |
| 51 | obstacle3 | theta |
| 52 | obstacle3 | static |
| 53 | obstacle3 | color_r |
| 54 | obstacle3 | color_g |
| 55 | obstacle3 | color_b |
| 56 | obstacle3 | z_order |
| 57 | obstacle3 | width |
| 58 | obstacle3 | height |
| 59 | obstacle4 | x |
| 60 | obstacle4 | y |
| 61 | obstacle4 | theta |
| 62 | obstacle4 | static |
| 63 | obstacle4 | color_r |
| 64 | obstacle4 | color_g |
| 65 | obstacle4 | color_b |
| 66 | obstacle4 | z_order |
| 67 | obstacle4 | width |
| 68 | obstacle4 | height |
| 69 | obstacle5 | x |
| 70 | obstacle5 | y |
| 71 | obstacle5 | theta |
| 72 | obstacle5 | static |
| 73 | obstacle5 | color_r |
| 74 | obstacle5 | color_g |
| 75 | obstacle5 | color_b |
| 76 | obstacle5 | z_order |
| 77 | obstacle5 | width |
| 78 | obstacle5 | height |
| 79 | obstacle6 | x |
| 80 | obstacle6 | y |
| 81 | obstacle6 | theta |
| 82 | obstacle6 | static |
| 83 | obstacle6 | color_r |
| 84 | obstacle6 | color_g |
| 85 | obstacle6 | color_b |
| 86 | obstacle6 | z_order |
| 87 | obstacle6 | width |
| 88 | obstacle6 | height |
| 89 | obstacle7 | x |
| 90 | obstacle7 | y |
| 91 | obstacle7 | theta |
| 92 | obstacle7 | static |
| 93 | obstacle7 | color_r |
| 94 | obstacle7 | color_g |
| 95 | obstacle7 | color_b |
| 96 | obstacle7 | z_order |
| 97 | obstacle7 | width |
| 98 | obstacle7 | height |
| 99 | obstacle8 | x |
| 100 | obstacle8 | y |
| 101 | obstacle8 | theta |
| 102 | obstacle8 | static |
| 103 | obstacle8 | color_r |
| 104 | obstacle8 | color_g |
| 105 | obstacle8 | color_b |
| 106 | obstacle8 | z_order |
| 107 | obstacle8 | width |
| 108 | obstacle8 | height |
| 109 | obstacle9 | x |
| 110 | obstacle9 | y |
| 111 | obstacle9 | theta |
| 112 | obstacle9 | static |
| 113 | obstacle9 | color_r |
| 114 | obstacle9 | color_g |
| 115 | obstacle9 | color_b |
| 116 | obstacle9 | z_order |
| 117 | obstacle9 | width |
| 118 | obstacle9 | height |


### Action Space
The entries of an array in this Box space correspond to the following action features:
| **Index** | **Feature** | **Description** | **Min** | **Max** |
| --- | --- | --- | --- | --- |
| 0 | dx | Change in robot x position (positive is right) | -0.050 | 0.050 |
| 1 | dy | Change in robot y position (positive is up) | -0.050 | 0.050 |
| 2 | dtheta | Change in robot angle in radians (positive is ccw) | -0.196 | 0.196 |
| 3 | darm | Change in robot arm length (positive is out) | -0.100 | 0.100 |
| 4 | vac | Directly sets the vacuum (0.0 is off, 1.0 is on) | 0.000 | 1.000 |


### Rewards
A penalty of -1.0 is given at every time step until termination, which occurs when the robot's position is within the target region.


### References
Narrow passages are a classic challenge in motion planning.
