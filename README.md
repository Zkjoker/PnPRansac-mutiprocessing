# PnPRansac-mutiprocessing
Reproduction and revision of solvePnPRansac algorithm

## Purpose<br>
1. This program is used in a project in my lab.<br><br>
2. **In this project, we change the PnPRansac algorithm and make it finishing iteration only when the current Rotation Matrix or Translation Vector has little change with last Rotation Matrix or Translation Vector no more than a threshold which can be set by user freely rather than finishing iteration when the algorithm reach the iteration times.**<br><br>

## Notice<br>
1. In our project this program is put in a neural network latter so the type of many variables is torch.Tensor(). In the program the input can be numpy.array() or t.Tensor(). But if you only use numpy.array(), you'd better to delete the related t.Tensor() variable for coding's efficiency.<br><br>
2. For fast running speed, We support two version of this algorithm: muti-ProReRansac.py and ProReRansac.py. The former is running for mutiprocessing(**Recommend to use this**). Of course you can change my code and make it available for cuda.<br><br>
3. In the code, notes are written by Chinese and output the state of system continuously. If you have any trouble for them please feel free to contact me. I will answer you soon.<br><br>
4. Pytorch 4.0 or higher version is ok, and it's usable for any numpy version.<br><br>

## File<br>
### Test Sample<br>
1. I support two test sample for interpret how my program work.<br><br>
2. 1.txt and 2.txt are two groundtruth poses for scenes_coordinate1.npy and scenes_coordinate2.npy.<br><br>
3. "scenes_coordinate1.npy" and "scenes_coordinate2.npy" is a 1×3×640×480 array. "640×480" record an image's image coordinates,and "3" record the world coordinates. In other words, if an array of a point (1,:,4,8)  is (7,6,5), which mean there is a point in the world and the world coordinate of the point is (7,6,5), and this point is record in current image for an image coordinate (4,8). This file is generated by saving an numpy.array(1×3×640×480).(**Notice: After reload it to program, it will be 1×3×480×640; But the real image is 3×640×480, (640 and 480 is reverse). Because this image can't be clockwise and counterclockwise rotate, so I readjust it in the code.You may adjust the code according to your circumstances.**)<br><br>
4. The transform matrices in 1.txt and 2.txt are Twc, which means:Pw=Twc·Pc, Pw is the world coordinate and Pc is the camera coordinate. <br><br>

### ReDefineError.py<br>
In this file there are three functions.They compute the reprojection error,angel error,and the difference of two transform matrix. Angel_error never be used in other files. <br><br>

## License
For commercial use，please leave a message to let me know.




