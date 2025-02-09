import numpy as np
import multiprocessing as mp
import cv2
import random
import time

def reprojection_error(Pose_Trans,Pos_world,Internal_ref,GT):
    'Pose_Trans：Tcw,，4×4; Pos_world:3×1；Inter_ref:内参,3×3；GT:2×1，均为numpy类型'
    R=Pose_Trans[0:3,0:3]
    trans=Pose_Trans[0:3,3:4]
    Pos_Cam=np.matmul(R,Pos_world)+ trans
    z=Pos_Cam[2]
    Pos_Nor=Pos_Cam / z

    Pos_Image = np.matmul(Internal_ref,Pos_Nor)
    Pos_Image=Pos_Image[0:2,:]
    loss=np.power(GT-Pos_Image,2)
    loss=np.sum(loss)
    reprojection_loss=np.sqrt(loss)
    return reprojection_loss

def angel_error(Pose_Trans,Pos_world,Internal_ref,GT):
    'Pose_Trans：Tcw,，4×4; Pos_world:3×1；Inter_ref:内参,3×3；GT:2×1;'
    Focal_len=Internal_ref[0][0]
    R=Pose_Trans[0:3,0:3]
    trans=Pose_Trans[0:3,3:4]
    Pos_Cam = np.matmul(R,Pos_world) + trans
    Inverse_ir=np.linalg.inv(Internal_ref)
    GT_normal=np.ones((3,1),dtype=np.float32)
    GT_normal[0:2,:]=GT[0:2,:]
    GT_Back2F=np.matmul(Inverse_ir,GT_normal)
    GT_Back2F=Focal_len * GT_Back2F
    dk=np.power(GT_Back2F,2)
    dk=np.sum(dk)
    dk=np.sqrt(dk)
    Dk=np.power(Pos_Cam,2)
    Dk=np.sum(Dk)
    Dk=np.sqrt(Dk)
    k=dk / Dk
    loss=(k*Pos_Cam)-GT_Back2F

    loss=np.power(loss,2)
    loss=np.sum(loss)
    angel_loss=np.sqrt(loss)
    return angel_loss

def Ran_Stard_test(Pic,CameraMatrix,distCoeffs):
    '直接调用cv2的pnpRansac算法，该函数作为对比'
    RanPw=[]
    RanPc=[]
    for i in range(Pic.shape[1]):
        for j in range(Pic.shape[2]):
            a=np.array(Pic[:, i, j])
            RanPw.append(a)
            RanPc.append(np.array([j,i]))

    RanPw=np.array(RanPw,dtype=np.float32)   #变为307200×3
    RanPc=np.array(RanPc,dtype=np.float32)

    _,R,trans,inliers=cv2.solvePnPRansac(RanPw,RanPc,CameraMatrix,distCoeffs,reprojectionError=10)
    r,_=cv2.Rodrigues(R)
    print('旋转平移的GT值为')
    print('R=',r)
    print('t=',trans)
    T=np.zeros((4,4),dtype=np.float32)
    T[0:3,0:3]=r
    T[0:3,3:4]=trans
    T[3][3]=1
    T_ni=np.linalg.inv(T)
    print('Tni=',T_ni)

    ra=random.randint(0,4799)
    pos_world=np.expand_dims((RanPw[ra]),axis=1)
    print('随机取pos_world=',pos_world)
    zer=np.zeros((3,1),dtype=np.float32)
    pos_image=np.expand_dims(RanPc[ra],axis=1)
    reloss = reprojection_error(Pose_Trans=T, Pos_world=pos_world, Internal_ref=CameraMatrix, GT=pos_image)
    anloss=angel_error(Pose_Trans=T,Pos_world=pos_world,Internal_ref=CameraMatrix,GT=pos_image)
    print('re_loss=',reloss)
    print('anloss=',anloss)
    print('如果误差较大，观察posworld是否都是0，如果是，重新运行，是随机取样的点不对')

def init():
    '初始化各项'
    Pic= np.load('scenes_coordinate2.npy')   ##大小为1×3×480×640
    Pic = np.squeeze(Pic)   #压缩掉第一维1
    Pic = np.array(Pic, dtype=np.float32)

    distCoeffs = np.zeros(5, dtype=np.float32)

    CameraMatrix = np.array([[525, 0, 324],
                             [0, 525, 244],
                             [0, 0, 1]], dtype=np.float32)
    return Pic,distCoeffs,CameraMatrix

def Get_World_Pos(PointSet,WH_3Pw):
    '从选出图像点中得到图像点对应的世界坐标系下的坐标'
    long=PointSet.shape[0]
    Point=np.zeros((long,3),dtype=np.float32)
    for i in range(long):
        x=int(PointSet[i][1])
        y=int(PointSet[i][0])      ##由于图像颠倒,ij换位
        pw = WH_3Pw[:,x,y]
        Point[i]=pw
    return Point

def Select256Rt(WH_3Pw,CameraMatrix,repro_threshold,distCoeffs):
    '选择256个重投影超过阈值的位姿:  WH_3Pw:3×w/8×h/8;  CameraMatrix: numpy，3×3；distCoeffs：numpy'

    Pic_width = WH_3Pw.shape[1]
    Pic_height = WH_3Pw.shape[2]
    Choose_point = np.zeros((Pic_width, Pic_height), dtype=np.int)  ##创建初始全0矩阵480×640，选过的点记为1
    Rt_set = []
    num_Rt = 0
    while (num_Rt != 256):  ##选256个Rt
        choose1 = random.randint(0, Pic_width - 1)     #0~479
        choose2 = random.randint(0, Pic_height - 1)    #0~639
        Four_point_set = []
        Num_of_Fourset = 0
        while (Num_of_Fourset < 4):  # 选4个点
            if (Choose_point[choose1][choose2] == 0):  ##点还未选过，可以用
                Four_point_set.append([choose2, choose1])    ##  由于图像颠倒，i,j 换位
                Num_of_Fourset = Num_of_Fourset + 1  ##四点组中组数+1
            choose1 = random.randint(0, Pic_width - 1)
            choose2 = random.randint(0, Pic_height - 1)
        ##到此为止 未重复的四点组合已经选入FourPointSet中，大小为4×2  等待确认是否可用

        P4image = np.array(Four_point_set, dtype=np.float32)  # 把四点组的图像坐标转变为numpy格式
        P4w = Get_World_Pos(P4image, WH_3Pw)  # 得到四点组的世界坐标，大小为4×3

        # 计算位姿
        bool, Rotate, trans = cv2.solvePnP(P4w, P4image, CameraMatrix, distCoeffs)


        #得到大T矩阵
        Rotate, _ = cv2.Rodrigues(Rotate)

        TT = np.zeros((4, 4),dtype=np.float32)
        TT[0:3, 0:3] = Rotate
        TT[0:3, 3:4] = trans
        TT[3][3] = 1

        Ok_flag = True
        for pw,pp in zip(P4w,P4image):
            pw=np.expand_dims(pw,axis=1)  ##把一个点的世界坐标系变为3×1的大小


            pp=np.expand_dims(pp,axis=1)  ##把一个点的图像坐标系变为2×1的大小


            RepreError = reprojection_error(TT, pw, CameraMatrix, pp)
            print(RepreError)
            if ( RepreError > repro_threshold):
                Ok_flag = False
                print("大于阈值"+str(repro_threshold)+",跳过重选")
                break     ##四点组要是有一个小于阈值，则重新来,退出 for pw,pp in zip(……)，之后的全部写在flag==True里面

        # 在阈值范围内，保存Rt，修改初始记点矩阵
        if (Ok_flag == True):
            Rt_set.append(TT)  ##保存T
            num_Rt = num_Rt + 1  # 保存了一个Rt
            print('重投影阈值设置为' + str(repro_threshold) +' 四点重投影误差均小于阈值，已被记录，当前共' + str(num_Rt) + '个Rt位姿')
            for pp in Four_point_set:
                x = int(pp[0])
                y = int(pp[1])
                Choose_point[y][x] = 1  ##记为四个点已经用过,xy调换
    print('256个位姿已经选择完成！')
    show=random.randint(0,255)
    print('随机取第'+str(show)+'个位姿展示：（该位姿未必正确）')
    print(np.linalg.inv(Rt_set[show]))   ##本身Rt为tensor类型，为显示更多的位数，拿np显示，取随机展示观察,该位姿未必正确
    return Rt_set

def compute_inliers(Rt,WH_3Pw,CameraMatrix,repro_threshold):   ##传入Rt，计算其对应内点
    '功能函数，传入一个Rt和三维图像矩阵，计算其对应的内点，该函数最为耗时，注意调整下采样指数！！'
    Numof_downsampe=int(8) ##采样指数，算480*640则改成int(1)，算60*80则用int(8)
    Pic_world = []
    Pic_image = []
    height = WH_3Pw.shape[1] / Numof_downsampe
    height = int(height)
    width = WH_3Pw.shape[2] / Numof_downsampe
    width = int(width)
    for x in range(height):
        for y in range(width):
            Pic_world.append(np.expand_dims(WH_3Pw[:, Numof_downsampe * x, Numof_downsampe * y],
                                                     axis=1))  ##WH_3Pw[:, x, y]为大小为3的数组，加一个轴变为3×1大小
            Pic_image.append(np.array([[Numof_downsampe * y],
                                                    [Numof_downsampe * x]], dtype=np.float32))
    inliers_map = []
    Num_inlier=0
    for pos_world, pos_img in zip(Pic_world, Pic_image):
        loss = reprojection_error(Pose_Trans=Rt, Pos_world=pos_world, Internal_ref=CameraMatrix,
                                  GT=pos_img)
        if (loss < repro_threshold):
            x = pos_img[0][0]
            y = pos_img[1][0]
            inliers_map.append([x, y])  # 记录内点图
            Num_inlier=Num_inlier+1
    print('正在计算，请等待256个位姿全部计算完成……')
    return Num_inlier,np.array(inliers_map,dtype=np.float32)

def muti_compute_inlier(parm):
    '''为多进程调用compute_inliers函数'''
    return compute_inliers(parm[0],parm[1],parm[2],parm[3])

def Rt_compute_Dsample_Point(WH_3Pw,CameraMatrix,repro_threshold,distCoeffs):
    '''计算256个位姿中内点数最多的位姿，输入np：WH_3Pw: [3,w/8,h/8];
    CameraMatrix:内参,3×3; repro_threshold：重投影阈值,常数'''

    Rt_set=Select256Rt(WH_3Pw=WH_3Pw,CameraMatrix=CameraMatrix,repro_threshold=repro_threshold,distCoeffs=distCoeffs)
    parms=[]
    for i in range(256):
        parm=(Rt_set[i], WH_3Pw, CameraMatrix, repro_threshold)
        parms.append(parm)   ##多进程工作，打包至parms元组内
    print('依次计算256个位姿对应内点：')
    startt=time.time()
    pool = mp.Pool(processes=10)
    Return=pool.map(muti_compute_inlier,parms) ##返回一个有256个元素的元组，每个元素也是一个有2个元素的元组，该元组第一个是内点数，第二个是内点
    MAX=Return[0][0]  ##设内点数最多的是第一个位姿
    best_index=0 #设最佳位姿索引数是第一个
    best_Inlier=Return[0][1] #最佳位姿的内点图
    end1=time.time()
    print('256个位姿变换及其对应内点计算完成,共耗时', end1 - startt)
    for i,pair in enumerate(Return):
        if (pair[0]>MAX):
            MAX=pair[0]
            best_index=i
    end2=time.time()
    print('第'+str(best_index)+'个位姿在阈值内的个数最多，最多为：'+str(MAX)+'个')
    print('对应位姿为:',np.linalg.inv(Rt_set[best_index]))
    Inlier=np.array(best_Inlier,dtype=np.float32)
    print('\n内点图大小为:',Inlier.shape)

    return Rt_set[best_index],Inlier    ##Rt，Inlier为numpy类型

def end_iter_thresh(TMat1,TMat2):
    '控制Ransac算法最后停止迭代'
    RMat1=TMat1[0:3,0:3]
    tMat1=TMat1[0:3,3:4]
    RMat2 = TMat2[0:3, 0:3]
    tMat2 = TMat2[0:3, 3:4]
    t_diff=np.power((tMat2-tMat1),2)
    t_diff=np.sum(t_diff)
    t_diff=np.sqrt(t_diff)
    print('t_diff=',t_diff)

    RMat2_t=np.transpose(RMat2)
    rotDiff=np.matmul(RMat1,RMat2_t)
    trace=np.trace(rotDiff)
    high=3
    low=-1
    if(trace > high):
        trace=high
    if(trace < low):
        trace=low
    ACos=np.arccos((trace-1)/2)
    roterr=180 * ACos /3.141592653
    print('roterr_diff=',roterr)

    return max(t_diff,roterr)

def Custom_Ransac(WH_3Pw,CameraMatrix,repro_threshold,distCoeffs,finish_iter_threshold):
    '''输入np和tensor都可以：WH_3Pw: [3,w/8,h/8]; CameraMatrix:内参,3×3; repro_threshold：重投影阈值,常数'''

    Rt,Inlier=Rt_compute_Dsample_Point(WH_3Pw=WH_3Pw,CameraMatrix=CameraMatrix,repro_threshold=repro_threshold,
                                        distCoeffs=distCoeffs)   #获取256个位姿下内点最多的位姿及其对应内点

    Pw=Get_World_Pos(Inlier, WH_3Pw)  #获取对应内点的世界坐标系

    Pw=np.ascontiguousarray(Pw)
    Inlier=np.ascontiguousarray(Inlier)

    bool_,Rotate,trans=cv2.solvePnP(Pw,Inlier,CameraMatrix,distCoeffs)
    Rotate, _ = cv2.Rodrigues(Rotate)


    new_Rt = np.zeros((4, 4),dtype=np.float32)
    new_Rt[0:3, 0:3] = Rotate
    new_Rt[0:3, 3:4] = trans
    new_Rt[3][3] = 1
    print('求出新的位姿变换：')
    print(new_Rt)

    diff=end_iter_thresh(Rt,new_Rt)
    print('与前一位姿差值为：',diff)
    Num=0
    while(diff > finish_iter_threshold): #开始迭代
        Num=Num+1
        print('设置终止阈值为',finish_iter_threshold,',该差值大于终止阈值，循环继续，当前正在进行第%s轮循环。'%Num)
        Orign_Rt=new_Rt

        _,Inliers_map=compute_inliers(Orign_Rt,WH_3Pw,CameraMatrix,repro_threshold)
        Pw = Get_World_Pos(Inliers_map, WH_3Pw)

        Pw1 = np.ascontiguousarray(Pw)
        Inlier1 = np.ascontiguousarray(Inliers_map)


        bool_, Rotate, trans = cv2.solvePnP(Pw1, Inlier1, CameraMatrix, distCoeffs)
        Rotate, _ = cv2.Rodrigues(Rotate)


        new_Rt =np.zeros((4, 4),dtype=np.float32)
        new_Rt[0:3, 0:3] = Rotate
        new_Rt[0:3, 3:4] = trans
        new_Rt[3][3] = 1
        print('求出新的位姿变换：')
        print('newrt=',np.linalg.inv(new_Rt))
        print('orignrt=',np.linalg.inv(Orign_Rt))
        diff = end_iter_thresh(Orign_Rt, new_Rt)
        print('与前一位姿差值为：', diff)

    print('与前一时刻位姿相差小于阈值',finish_iter_threshold,',循环结束,求出位姿。')
    print('最终位姿为：')
    print(np.linalg.inv(new_Rt))



if __name__=='__main__':
    start=time.time()
    Pic,distCoeffs, CameraMatrix=init()
    #Ran_Stard_test(Pic=Pic, CameraMatrix=CameraMatrix, distCoeffs=distCoeffs)  # 此句用来验证标准PnPRansac输出,测试完成
    ##此句用来验证选择256位姿正确性，测试完成:
    #Rt_set = Select256Rt(WH_3Pw=Pic, CameraMatrix=CameraMatrix, repro_threshold=10, distCoeffs=distCoeffs)

   #此句用来验证选择内点最多的256位姿之一算法，测试完成
   #Rt_compute_Dsample_Point(WH_3Pw=Pic, CameraMatrix=CameraMatrix, repro_threshold=10, distCoeffs=distCoeffs)

    Custom_Ransac(WH_3Pw=Pic, CameraMatrix=CameraMatrix, repro_threshold=1, distCoeffs=distCoeffs,finish_iter_threshold=0.0000000005)
    end=time.time()
    print('程序结束，耗时%d秒'%(end-start))
