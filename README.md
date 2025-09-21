# PennApps XXVI Submission
### Authors: Aditya Choudhary, Akshat Tewari, Saketh Satti


# Inspiration
We have all had experience with drones, and it is our hobby. We had done competitions where the idea was to make a drone that would pick up a payload and drop it off somewhere else. However, we had never attempted to make an autonomous drone or do anything in search and rescue.
What it does

Search and rescue has traditionally been carried out by ground teams. Recently, drones have been introduced into the process, as they can cover land quickly, provide elevated vantage points, and reduce search time. Most drone search algorithms, however, rely on a simple lawn mower pattern, which assumes that missing individuals remain stationary. In reality, people who are lost often move in an attempt to reach safety. Our statistical model incorporates human psychology to better predict this movement. For example, when someone reaches a river, they are unlikely to cross it and will instead tend to follow the water’s course. We also have a Raspberry Pi camera that will use a yolo model to look for humans. We also have Gemini running to compare the last description and image of the person with any humans found to see if we found the right person.

# How we built it
We started by designing the drone’s core framework and installing a Raspberry Pi as the companion computer. The statistical movement model was implemented in Python, using behavioral patterns documented in real-world search and rescue research (Lost person behavior by Koester, Robert J). We made a Monte Carlo Simulation, which simulated a bunch of humans in the terrain of the lost individual. The YOLO object detection model was trained and optimized for efficiency so it could run on the Pi’s limited resources. Gemini was connected through an API to process descriptive data and compare live camera detections with the provided references. We integrated all of these systems into a unified pipeline that guides the drone’s path, detects humans, and verifies possible matches.

# Challenges we ran into
We faced several challenges throughout this project, including efficiently running YOLO on the Raspberry Pi’s limited computing power, calibrating our movement prediction model to handle the complexity of real-world environments, integrating Gemini smoothly into our real-time detection pipeline, and maintaining drone flight stability while simultaneously running detection and path-planning software. From these difficulties, we learned how to optimize machine learning models for resource-constrained devices, design movement prediction systems that balance statistics with practical human behavior, and integrate multiple AI modules into a cohesive pipeline. We also gained experience in systems integration and real-time debugging, which highlighted the importance of balancing hardware limits with software goals. Ultimately, this project taught us how multidisciplinary search and rescue truly is, blending AI, robotics, psychology, and hardware optimization, and gave us far more insights than we expected when we began.

# Accomplishments that we're proud of
Developing a working prototype where drones don’t just search blindly, but actually predict where missing people are most likely to move.

Successfully deploying YOLO on the Raspberry Pi in a lightweight form.

Creating a pipeline that combines detection with verification, reducing false positives in human searches.

Pioneering an approach that merges drone technology, AI, and psychology into a single unified search system.

# What we learned
We learned how we can use our passion for drones for the betterment of the world. We learned how to optimize machine learning models to run on resource-constrained devices like the Raspberry Pi. We gained experience in integrating multiple AI systems and handling interoperability between them. Most importantly, we discovered how search and rescue involves not just technology, but also an understanding of human behavior and psychology. Combining those two fields gave us new insight into how AI can be applied to real-world safety challenges.

# What's next for SARTech
We plan to improve the efficiency of our path prediction model by training it with larger datasets from real-world search and rescue operations. We want to expand beyond rivers and simple terrain factors to account for obstacles like cliffs. On the detection side, we intend to experiment with thermal imaging to improve performance in low-light or obstructed conditions. Finally, we envision scaling SARTech into a deployable tool that rescue teams can use in the field—helping save lives by combining autonomous flight, intelligent search, and human-centered prediction.
