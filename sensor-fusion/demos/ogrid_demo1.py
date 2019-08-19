# Michael P. Hayes UCECE, Copyright 2018--2019
import numpy as np
from matplotlib.pyplot import arrow
from ipywidgets import interact, interactive, fixed
from matplotlib.pyplot import subplots
from .lib.robot import robot_draw, Robot
from .lib.pose import Pose

xmin = -10
xmax = 10
ymin = 0
ymax = 10
tmin = -180
tmax = 180

Nx = 21
Ny = 11

x = np.linspace(xmin, xmax, Nx)
y = np.linspace(ymin, ymax, Ny)

beamwidth = 15

class Line(object):

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        
    @property
    def A(self):
        return self.p1[1] - self.p2[1]
    
    @property
    def B(self):        
        return self.p2[0] - self.p1[0]
    
    @property
    def C(self):
        return self.p2[0] * self.p1[1] - self.p1[0] * self.p2[1]
    
    def intersection(self, line):
        
        if not isinstance(line, Line):
            line = Line(*line)
            
        D  = self.A * line.B - self.B * line.A
        Dx = self.C * line.B - self.B * line.C
        Dy = self.A * line.C - self.C * line.A
        
        if D == 0:
            return False
        x = Dx / D
        y = Dy / D
        return x, y

    def coord(self, t):

        x = self.p1[0] + t * (self.p2[0] - self.p1[0])
        y = self.p1[1] + t * (self.p2[1] - self.p1[1])
        return x, y

    
class LineSeg(Line):

    def intersection(self, lineseg):
        R = super(LineSeg, self).intersection(lineseg)
        if not R:
            return False
        x, y = R

        tx = (x - self.p1[0]) / (self.p2[0] - self.p1[0] + 1e-20)
        ty = (y - self.p1[1]) / (self.p2[1] - self.p1[1] + 1e-20)
        if tx > 1 or tx < 0:
            return False
        if ty > 1 or ty < 0:
            return False

        tx = (x - lineseg.p1[0]) / (lineseg.p2[0] - lineseg.p1[0] + 1e-20)
        ty = (y - lineseg.p1[1]) / (lineseg.p2[1] - lineseg.p1[1] + 1e-20)
        if tx > 1 or tx < 0:
            return False
        if ty > 1 or ty < 0:
            return False        
        
        return R

    @property
    def length(self):

        return np.sqrt((self.p2[0] - self.p1[0])**2 +
                       (self.p2[1] - self.p1[1])**2)
    

class Scan(object):

    def __init__(self, angles, ranges, rmax):
        self.angles = angles
        self.ranges = ranges
        self.rmax = rmax

        
class Rangefinder(object):

    def __init__(self, beamwidth, rmax=20):
        self.beamwidth = beamwidth
        self.rmax = rmax

    def scan(self, pose, walls, dangle=np.radians(1)):

        xr, yr, hr = pose.x, pose.y, pose.theta

        Nrays = int(np.ceil(self.beamwidth / dangle))
        angles = np.linspace(hr - 0.5 * (self.beamwidth - dangle),
                             hr + 0.5 * (self.beamwidth - dangle), Nrays)

        ranges = angles * 0
        
        for m, angle in enumerate(angles):

            x = xr + np.cos(angle) * self.rmax
            y = yr + np.sin(angle) * self.rmax

            lineseg = LineSeg((xr, yr), (x, y))

            rmin = self.rmax
            for wall in walls:
                R = lineseg.intersection(wall.lineseg)
                if R:
                    xt, yt = R
                    r = np.sqrt((xr - xt)**2 + (yr - yt)**2)
                    if r < rmin:
                        rmin = r
            ranges[m] = rmin

        return Scan(angles, ranges, self.rmax)
        
        
    def draw_beam(self, axes, pose, walls=[], **kwargs):
        # Ignore walls for now...
    
        xmin, xmax = axes.get_xlim()
        ymin, ymax = axes.get_ylim()
        
        axes.set_xlim(xmin, xmax)
        axes.set_ylim(ymin, ymax)        

        xr, yr, hr = pose.x, pose.y, pose.theta        

        dangle = np.radians(1)
        scan = self.scan(pose, walls, dangle)

        for angle, r in zip(scan.angles, scan.ranges):
        
            t1 = angle - 0.5 * dangle
            t2 = angle + 0.5 * dangle
                        
            x1 = xr + np.cos(t1) * r
            x2 = xr + np.cos(t2) * r
            y1 = yr + np.sin(t1) * r
            y2 = yr + np.sin(t2) * r
            
            axes.fill((xr, x1, x2), (yr, y1, y2),
                      alpha=kwargs.pop('alpha', 0.5),
                      color=kwargs.pop('color', 'tab:blue'),
                      **kwargs)

class Occfind(object):

    def __init__(self, pose, scan):
        self.pose = pose
        self.scan = scan

    def hits(self):

        hits = {}

        for angle, r in zip(self.scan.angles, self.scan.ranges):

            if r >= self.scan.rmax:
                continue
            xt = self.pose.x + r * np.cos(angle)
            yt = self.pose.y + r * np.sin(angle)

            xc = int(xt + 0.5)
            yc = int(yt + 0.5)
            hit = (xc, yc)

            if hit not in hits:
                hits[hit] = 0
            hits[hit] += 1
        return hits

    def visits(self):

        dr = 0.1
        visits = {}

        for angle, r in zip(self.scan.angles, self.scan.ranges):

            xt = self.pose.x + r * np.cos(angle)
            yt = self.pose.y + r * np.sin(angle)

            lineseg = LineSeg((self.pose.x, self.pose.y),
                              (xt, yt))

            length = lineseg.length
            steps = int(length / dr + 0.5)
            t = np.linspace(0, 1, steps)

            for t1 in t:
                xt, yt = lineseg.coord(t1)
                xc = int(xt + 0.5)
                yc = int(yt + 0.5)
                visit = (xc, yc)

                if visit not in visits:
                    visits[visit] = 0
                visits[visit] += 1
        return visits    

    def hits_misses(self):

        hits = self.hits()
        visits = self.visits()

        misses = {}
        for visit in visits:
            if visit not in hits:
                misses[visit] = visits[visit]
        return hits, misses
    
            
class Wall(object):

    def __init__(self, p1, p2):

        self.lineseg = LineSeg(p1, p2)
        
        self.x = (p1[0], p2[0])
        self.y = (p1[1], p2[1])

    def draw(self, axes):

        axes.plot(self.x, self.y, 'k')

wall1 = Wall((-1, 8), (4, 8))
wall2 = Wall((4, 8), (4, 6))
walls = (wall1, wall2)
        

def heatmap(ax, x, y, data, fmt='%.1f', skip=[], **kwargs):

    dx = x[1] - x[0]
    dy = y[1] - y[0]

    # These are the corners.
    xc = np.linspace(x[0] - dx / 2, x[-1] + dx / 2, len(x) + 1)
    yc = np.linspace(y[0] - dy / 2, y[-1] + dy / 2, len(y) + 1)    
    
    c = ax.pcolor(xc, yc, data, linewidths=4, vmin=0.0, vmax=1.0,
                  edgecolors=kwargs.pop('edgecolors', 'w'),
                  cmap=kwargs.pop('cmap', 'RdBu'),
                  **kwargs)

    c.update_scalarmappable()

    for p, color, value in zip(c.get_paths(), c.get_facecolors(), c.get_array()):
        x, y = p.vertices[:-2, :].mean(0)
        if np.all(color[:3] > 0.5):
            color = (0.0, 0.0, 0.0)
        else:
            color = (1.0, 1.0, 1.0)

        draw_text = True
        for skip1 in skip:
           xs, ys = skip1
           if abs(x - xs) < 0.1 and abs(y - ys) < 0.1:
               draw_text = False
               break

        if draw_text:
            ax.text(x, y, fmt % value, ha="center", va="center",
                    color=color, **kwargs)


class Ogrid(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y
        # Log odds
        self.grid = np.zeros((Ny, Nx))
        
    def draw(self, axes, skip=[]):
        # Convert log odds to probability
        P = 1 - 1 / (1 + np.exp(self.grid))
        heatmap(axes, self.x, self.y, P, skip=skip)

    def update(self, cells, P1, P2):

        lam = np.log(P1 / P2)
        for cell in cells:
            # Weed out marginal cells.
            if cells[cell] < 5:
                continue

            try:
                m = np.argwhere(self.x == cell[0])[0][0]
                n = np.argwhere(self.y == cell[1])[0][0]            
                self.grid[n, m] += lam
            except:
                pass
                
        
ogrid = Ogrid(x, y)
rangefinder = Rangefinder(np.radians(beamwidth))

        
def ogrid_demo1_plot(x=3, y=1, heading=75):

    robot = Robot(x, y, heading=np.radians(heading))    

    scan = rangefinder.scan(robot.pose, walls)
    hits, misses = Occfind(robot.pose, scan).hits_misses()

    ogrid.update({(robot.x, robot.y): 100}, 0.001, 1)
    ogrid.update(hits, 0.06, 0.005)
    ogrid.update(misses, 0.2, 0.9)    
    
    fig, ax = subplots(figsize=(10, 5))
    ax.axis('equal')
    ogrid.draw(ax, ((robot.x, robot.y), ))
    robot.draw(ax)
    for wall in walls:
        wall.draw(ax)
    rangefinder.draw_beam(ax, robot.pose, walls=walls)

    
def ogrid_demo1():
    interact(ogrid_demo1_plot,
             x=(xmin, xmax, 1),
             y=(ymin, ymax, 1),
             heading=(tmin, tmax, 15),              
             continuous_update=False)
    
