# Inverse kinematics

> Source: English Wikipedia, article "Inverse kinematics" (CC BY-SA 4.0).

In computer animation and robotics, inverse kinematics (IK) is the mathematical process of calculating the variable joint parameters needed to place the end of a kinematic chain, such as a robot manipulator or an animation rig's hand or foot, in a given position and orientation (relative to the start of the chain). IK operations are computationally much more complex than forward kinematics, in which joint parameters are trigonometrically calculated to achieve the position and orientation of the chain's end.


## Robotics

In robotics, inverse kinematics makes use of the kinematics equations to determine the joint parameters that provide a desired configuration (position and rotation) for each of the robot's end effectors. This is important because robot tasks are performed with the end effectors, while control effort applies to the joints. Determining the movement of a robot so that its end effectors move from an initial configuration to a desired configuration is known as motion planning. Inverse kinematics transforms the motion plan into joint actuator trajectories for the robot. Similar formulas determine the positions of the skeleton of an animated character that is to move in a particular way in a film, or of a vehicle such as a car or boat containing the camera which is shooting a scene of a film. Once a vehicle's motions are known, they can be used to determine the constantly changing viewpoint for computer-generated imagery of objects in the landscape such as buildings, so that these objects change in perspective while themselves not appearing to move as the vehicle-borne camera goes past them.
The movement of a kinematic chain, whether it is a robot or an animated character, is modeled by the kinematics equations of the chain.  These equations define the configuration of the chain in terms of its joint parameters.  Forward kinematics uses the joint parameters to compute the configuration of the chain, and inverse kinematics reverses this calculation to determine the joint parameters that achieve a desired configuration.


## Kinematic analysis

Kinematic analysis is one of the first steps in the design of most industrial robots. Kinematic analysis allows the designer to obtain information on the position of each component within the mechanical system. This information is necessary for subsequent dynamic analysis along with control paths.
Inverse kinematics is an example of the kinematic analysis of a constrained system of rigid bodies, or kinematic chain.  The kinematic equations of a robot can be used to define the loop equations of a complex articulated system.  These loop equations are nonlinear constraints on the configuration parameters of the system.  The independent parameters in these equations are known as the degrees of freedom of the system.
While analytical solutions to the inverse kinematics problem exist for a wide range of kinematic chains, computer modeling and animation tools often use Newton's method to solve the nonlinear kinematics equations. When trying to find an analytical solution it is often convenient to exploit the geometry of the system and decompose it using subproblems with known solutions.
Other applications of inverse kinematic algorithms include interactive manipulation, animation control and collision avoidance.


## Inverse kinematics and 3D animation

Inverse kinematics is important to game programming and 3D animation, where it is used to connect game characters physically to the world, such as feet landing firmly on top of terrain.
An animated figure is modeled with a skeleton of rigid segments connected with joints, called a kinematic chain.  The kinematics equations of the figure define the relationship between the joint angles of the figure and its pose or configuration.  The forward kinematic animation problem uses the kinematics equations to determine the pose given the joint angles.   The inverse kinematics problem computes the joint angles for a desired pose of the figure.
It is often easier for computer-based designers, artists, and animators to define the spatial configuration of an assembly or figure by moving parts, or arms and legs, rather than directly manipulating joint angles.  Therefore, inverse kinematics is used in computer-aided design systems to animate assemblies and by computer-based artists and animators to position figures and characters.
The assembly is modeled as rigid links connected by joints that are defined as mates, or geometric constraints.  Movement of one element requires the computation of the joint angles for the other elements to maintain the joint constraints.  For example, inverse kinematics allows an artist to move the hand of a 3D human model to a desired position and orientation and have an algorithm select the proper angles of the wrist, elbow, and shoulder joints.  Successful implementation of computer animation usually also requires that the figure move within reasonable anthropomorphic limits.
A method of comparing both forward and inverse kinematics for the animation of a character can be defined by the advantages inherent to each. For instance, blocking animation where large motion arcs are used is often more advantageous in forward kinematics. However, more delicate animation and positioning of the target end effector in relation to other models might be easier using inverted kinematics. Modern digital creation packages (DCC) offer methods to apply both forward and inverse kinematics to models.


## Analytical solutions to inverse kinematics


### Generic solutions
In some, but not all cases, there exist analytical solutions to inverse kinematic problems. One such example is for a robot with 6 degrees of freedom (DOF) (for example, 6 revolute joints) moving in 3D space (with 3-position DOF, and 3 rotational DOF). If the DOF of the robot equals or exceeds that of the end effector, for example with a 7-DoF robot with 7 revolute joints, then there exist infinitely many solutions to the IK problem and an analytical solution does not exist. Further extending this example, it is possible to fix one joint and analytically solve for the other joints, but a better solution is perhaps offered by numerical methods, which can instead optimize a solution given additional preferences (costs in an optimization problem).
An analytic solution to an inverse kinematics problem is a closed-form expression that takes the end-effector pose as input and gives joint positions as output, 
  
    
      
        q
        =
        f
        (
        x
        )
      
    
    {\displaystyle q=f(x)}
  
. Analytical inverse kinematics solvers can be significantly faster than numerical solvers and provide more than one solution, but only a finite number of solutions, for a given end-effector pose.
Many different programs (Such as FOSS programs IKFast and Inverse Kinematics Library) are able to solve these problems quickly and efficiently using different algorithms such as the FABRIK solver. One issue with these solvers, is that they are known to not necessarily give locally smooth solutions between two adjacent configurations, which can cause instability if iterative solutions to inverse kinematics are required, such as if the IK is solved inside a high-rate control loop.


### Ortho-parallel basis and a spherical wrist

Many industrial 6DOF robots feature three rotational joints with intersecting axes ("spherical wrist"). These robots, known as robots with an "Ortho-parallel Basis and a Spherical Wrist," can be defined by 7 kinematic parameters that are distances in their assumed standard geometry. These robots may have up to 8 independent solutions for any given position and rotation of the robot tool head. Open-source solutions for C++ and Rust exist. OPW has also been integrated into ROS framework. 


## Numerical solutions to IK problems
There are many methods of modelling and solving inverse kinematics problems. The most flexible of these methods typically rely on iterative optimization to seek out an approximate solution, due to the difficulty of inverting the forward kinematics equation and the possibility of an empty solution space. The core idea behind several of these methods is to model the forward kinematics equation using a Taylor series expansion, which can be simpler to invert and solve than the original system.


### The Jacobian inverse technique
The Jacobian inverse technique is a simple yet effective way of implementing inverse kinematics. Let there be 
  
    
      
        m
      
    
    {\displaystyle m}
  
 variables that govern the forward-kinematics equation, i.e. the position function. These variables may be joint angles, lengths, or other arbitrary real values. If, for example, the IK system lives in a 3-dimensional space, the position function can be viewed as a mapping 
  
    
      
        p
        (
        x
        )
        :
        
          
            R
          
          
            m
          
        
        →
        
          
            R
          
          
            3
          
        
      
    
    {\displaystyle p(x):\mathbb {R} ^{m}\rightarrow \mathbb {R} ^{3}}
  
. Let 
  
    
      
        
          p
          
            0
          
        
        =
        p
        (
        
          x
          
            0
          
        
        )
      
    
    {\displaystyle p_{0}=p(x_{0})}
  
 give the initial position of the system, and 

  
    
      
        
          p
          
            1
          
        
        =
        p
        (
        
          x
          
            0
          
        
        +
        Δ
        x
        )
      
    
    {\displaystyle p_{1}=p(x_{0}+\Delta x)}
  

be the goal position of the system. The Jacobian inverse technique iteratively computes an estimate of 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
 that minimizes the error given by

  
    
      
        
          |
        
        
          |
        
        p
        (
        
          x
          
            0
          
        
        +
        Δ
        
          x
          
            estimate
          
        
        )
        −
        
          p
          
            1
          
        
        
          |
        
        
          |
        
      
    
    {\displaystyle ||p(x_{0}+\Delta x_{\text{estimate}})-p_{1}||}
  
.
For small 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
-vectors, the series expansion of the position function gives

  
    
      
        p
        (
        
          x
          
            1
          
        
        )
        ≈
        p
        (
        
          x
          
            0
          
        
        )
        +
        
          J
          
            p
          
        
        (
        
          x
          
            0
          
        
        )
        Δ
        x
      
    
    {\displaystyle p(x_{1})\approx p(x_{0})+J_{p}(x_{0})\Delta x}
  
,
where 
  
    
      
        
          J
          
            p
          
        
        (
        
          x
          
            0
          
        
        )
      
    
    {\displaystyle J_{p}(x_{0})}
  
 is the (3 × m) Jacobian matrix of the position function at 
  
    
      
        
          x
          
            0
          
        
      
    
    {\displaystyle x_{0}}
  
.
The (i, k)-th entry of the Jacobian matrix can be approximated numerically

  
    
      
        
          
            
              ∂
              
                p
                
                  i
                
              
            
            
              ∂
              
                x
                
                  k
                
              
            
          
        
        ≈
        
          
            
              
                p
                
                  i
                
              
              (
              
                x
                
                  0
                  ,
                  k
                
              
              +
              h
              )
              −
              
                p
                
                  i
                
              
              (
              
                x
                
                  0
                
              
              )
            
            h
          
        
      
    
    {\displaystyle {\frac {\partial p_{i}}{\partial x_{k}}}\approx {\frac {p_{i}(x_{0,k}+h)-p_{i}(x_{0})}{h}}}
  
,
where 
  
    
      
        
          p
          
            i
          
        
        (
        x
        )
      
    
    {\displaystyle p_{i}(x)}
  
 gives the i-th component of the position function, 
  
    
      
        
          x
          
            0
            ,
            k
          
        
        +
        h
      
    
    {\displaystyle x_{0,k}+h}
  
 is simply 
  
    
      
        
          x
          
            0
          
        
      
    
    {\displaystyle x_{0}}
  
 with a small delta added to its k-th component, and 
  
    
      
        h
      
    
    {\displaystyle h}
  
 is a reasonably small positive value.
Taking the Moore–Penrose pseudoinverse of the Jacobian (computable using a singular value decomposition) and re-arranging terms results in

  
    
      
        Δ
        x
        ≈
        
          J
          
            p
          
          
            +
          
        
        (
        
          x
          
            0
          
        
        )
        Δ
        p
      
    
    {\displaystyle \Delta x\approx J_{p}^{+}(x_{0})\Delta p}
  
,
where 
  
    
      
        Δ
        p
        =
        p
        (
        
          x
          
            0
          
        
        +
        Δ
        x
        )
        −
        p
        (
        
          x
          
            0
          
        
        )
      
    
    {\displaystyle \Delta p=p(x_{0}+\Delta x)-p(x_{0})}
  
.
Applying the inverse Jacobian method once will result in a very rough estimate of the desired 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
-vector. A line search should be used to scale this 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
 to an acceptable value. The estimate for 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
 can be improved via the following algorithm (known as the Newton–Raphson method):

  
    
      
        Δ
        
          x
          
            k
            +
            1
          
        
        =
        
          J
          
            p
          
          
            +
          
        
        (
        
          x
          
            k
          
        
        )
        Δ
        
          p
          
            k
          
        
      
    
    {\displaystyle \Delta x_{k+1}=J_{p}^{+}(x_{k})\Delta p_{k}}
  

Once some 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
-vector has caused the error to drop close to zero, the algorithm should terminate. Existing methods based on the Hessian matrix of the system have been reported to converge to desired 
  
    
      
        Δ
        x
      
    
    {\displaystyle \Delta x}
  
 values using fewer iterations, though, in some cases more computational resources.


### Heuristic methods
The inverse kinematics problem can also be approximated using heuristic methods. These methods perform simple, iterative operations to gradually lead to an approximation of the solution. The heuristic algorithms have low computational cost (return the final pose very quickly), and usually support joint constraints. The most popular heuristic algorithms are cyclic coordinate descent (CCD) and forward and backward reaching inverse kinematics (FABRIK).


## See also


## References


## External links
Forward And Backward Reaching Inverse Kinematics (FABRIK)
Robotics and 3D Animation in FreeBasic (in Spanish)
Analytical Inverse Kinematics Solver - Given an OpenRAVE robot kinematics description, generates a C++ file that analytically solves for the complete IK.
Inverse Kinematics algorithms
Robot Inverse solution for a common robot geometry
HowStuffWorks.com article How do the characters in video games move so fluidly? with an explanation of inverse kinematics
3D animations of the calculation of the geometric inverse kinematics of an industrial robot
3D Theory Kinematics
Protein Inverse Kinematics
Simple Inverse Kinematics example with source code using Jacobian
Detailed description of Jacobian and CCD solutions for inverse kinematics
Autodesk HumanIK
A 3D visualization of an analytical solution of an industrial robot
