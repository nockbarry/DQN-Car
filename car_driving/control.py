import os
import sys

import numpy as np
import pygame
from pygame.locals import *
from pygame.math import Vector2
from shapely.geometry import Point, Polygon

import geometry

FILE_PATH = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(FILE_PATH, "images")
AUDIO_PATH = os.path.join(FILE_PATH, "audio")


def load_image(name, colorkey=None, scale=None):
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)
    image = image.convert()
    if scale:
        image = pygame.transform.scale(image, scale)
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, RLEACCEL)
    return image


def get_row(sprite_sheet,start_y,sprite_length):
    row = []
    for i in range(3):
        start_x = i*sprite_length
        row.append(sprite_sheet.subsurface(pygame.Rect(start_x, start_y, sprite_length, sprite_length)))
    return row

def get_sprite_grid(name):
    LEN_SPRT = 32
    sheet = load_image(os.path.join(
            IMAGE_PATH, name), -1)
    rows = {'updown':[], 'leftright': []}
    rows['updown'].append(get_row(sheet,96,32))
    rows['updown'].append(get_row(sheet,0,32))
    rows['leftright'].append(get_row(sheet,32,32))
    rows['leftright'].append(get_row(sheet,64,32))
    return rows


class RewardMarker(pygame.sprite.Sprite):
    def __init__(self, position=(0, 0), reward=-1):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((30, 30))
        self.image.fill(pygame.Color("red"))
        self.rect = self.image.get_rect(center=position)
        self.screen = pygame.display.get_surface()
        self.mask = pygame.mask.from_surface(self.image)
        self.reward = reward
        pygame.draw.circle(self.image, pygame.Color(
            "red"), self.rect.center, 15)

    def collect(self):
        r = self.reward
        self.reward = 0
        return r


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        # Init.
        pygame.sprite.Sprite.__init__(self)
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.color = color
        self.screen = pygame.display.get_surface()
        # Create
        self.image = pygame.Surface([width, height])
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.topleft = x, y
        self.mask = pygame.mask.from_surface(self.image)
        self.reward = 50

    @property
    def corners(self):
        return self.rect.topright, self.rect.bottomright, self.rect.bottomleft, self.rect.topleft

    @property
    def sides(self):
        return ((self.rect.topright, self.rect.bottomright),
                (self.rect.bottomright, self.rect.bottomleft),
                (self.rect.bottomleft, self.rect.topleft),
                (self.rect.topleft, self.rect.topright))

    @property
    def shapely_polygon(self):
        return Polygon(self.corners)


class Pedestrian(pygame.sprite.Sprite):
    def __init__(self, name, position=(0, 0), walking_direction='updown', walking_distance=60, speed=0.5):
        super().__init__()
        sprites = get_sprite_grid(name)
        self.directional_sprites = sprites[walking_direction]
        self.idx = 0
        self.dir_idx = 0
        self.images = self.directional_sprites[self.dir_idx]
        self.image = self.images[self.idx]
        self.rect = self.image.get_rect()
        self.pivot = Vector2(position)
        self.position = Vector2(self.pivot)
        self.distance = walking_distance
        self.speed = speed
        self.reward = 500
        self.direction = Vector2(0,-1)
        self.change_direction(walking_direction)
        self._update_mask()
        self.dead = False

    @property
    def sides(self):
        return ((self.rect.topright, self.rect.bottomright),
                (self.rect.bottomright, self.rect.bottomleft),
                (self.rect.bottomleft, self.rect.topleft),
                (self.rect.topleft, self.rect.topright))
        

    def _update_mask(self):
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.center = self.position

    def update(self):
        if self.dead:
            pass
        self.idx = (self.idx + 1) % 3
        self.image = self.images[self.idx]
        self.position += self.direction * self.speed
        if self.position - self.pivot == self.distance * self.direction:
            self.pivot = Vector2(self.position)
            self.invert_direction()
        self._update_mask()

    def invert_direction(self):
        self.direction *= -1
        self.dir_idx = int(not self.dir_idx)
        self.image_idx = 0
        self.images = self.directional_sprites[self.dir_idx]
        self.image = self.images[0]
    
    def change_direction(self, direction):
        self.image_idx = 0
        self.dir_idx = 0
        if direction=="updown":
            self.direction = Vector2(0,-1)
        elif direction=="leftright":
            self.direction = Vector2(-1,0)
        else:
            raise Exception('ur direction dont exist boi.')
        self.images = self.directional_sprites[self.dir_idx]
        self.image = self.images[0]
 


class Car(pygame.sprite.Sprite):
    def __init__(self, position=(0, 0)):
        pygame.sprite.Sprite.__init__(self)
        self.original_image = load_image(os.path.join(
            IMAGE_PATH, 'car_sprite.bmp'), -1, (40, 30))
        self.image = self.original_image
        self.rect = self.image.get_rect(center=position)
        self.mask = pygame.mask.from_surface(self.image)
        self.position = Vector2(position)
        self.direction = Vector2(1,0)
        self.screen = pygame.display.get_surface().get_rect()
        self.speed = 0
        self.MAX_FORWARD = 5
        self.MAX_REVERSE = -3
        self.angle = 0
        self.age = 0
        self.reward = 0

    def _update_mask(self):
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.center = self.position

    # Thanks @ https://stackoverflow.com/questions/45889954/rotating-and-moving-a-sprite-in-pygame
    def rotate(self, angle):
        if angle != 0:
            # Rotate the direction vector and then the image.
            self.direction.rotate_ip(angle)
            self.angle += angle
            self.image = pygame.transform.rotate(
                self.original_image, -self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)
            self._update_mask()

    def accelerate(self, accel):
        assert -1 <= accel <= 1
        newspeed = self.speed + accel
        if newspeed > self.MAX_FORWARD:
            self.speed = self.MAX_FORWARD
        elif newspeed < self.MAX_REVERSE:
            self.speed = self.MAX_REVERSE
        else:
            self.speed = newspeed

    def _crash(self):
        self.position += self.direction * -3*np.sign(self.speed)
        self.rect.center = self.position
        self.speed = -0.1*np.sign(self.speed)

    def _move(self):
        # Update the position vector and the rect.
        new_pos = self.position + self.direction * self.speed
        if not self.screen.collidepoint(tuple(new_pos)):
            self._crash()
        else:
            self.position = new_pos
        self.rect.center = self.position
        self.reward -= 1/10

    def handle_collisions(self, walls=[], pedestrians = [],reward_markers=[]):
        for wall in walls:
            if pygame.sprite.collide_mask(self, wall):
                # reward proportional to speed for hitting into wall
                self.reward -= wall.reward*np.abs(self.speed)
                self._crash()
        for ped in pedestrians:
            if not ped.dead and pygame.sprite.collide_mask(self,ped):
                self.reward -= ped.reward
                self._crash()
                ped.kill()
                ped.dead=True
        for rw in reward_markers:
            if pygame.sprite.collide_mask(self, rw):
                self.reward += rw.collect()

    def observe(self, walls):
        obs = np.ones((72,1), dtype=np.float16)*100
        for i in range(len(obs)):
            theta = 360/len(obs)*i
            ray = self.position + self.direction.rotate(theta)*100
            ray_segment = (tuple(self.position), tuple(ray))
           # pygame.draw.line(pygame.display.get_surface(), (255,0,0), (tuple(self.position)), tuple(ray))
            #pygame.draw.line(pygame.display.get_surface(), (0,0,0), (tuple(self.position)), tuple(self.position+self.direction*50))
            for wall in walls:
                for side in wall.sides:
                    found = geometry.intersects(ray_segment, side) or geometry.intersects(side, ray_segment)
                    if found:
                        try:
                            intersection = geometry.get_intersection(
                                ray_segment[0], ray_segment[1], side[0], side[1])
                            distance = geometry.distance(
                                self.position, intersection)
                            if distance < obs[i][0]:
                              #  pygame.draw.circle(pygame.display.get_surface(), (0,255,0), intersection,3)
                                obs[i][0] = distance
                        except Exception as e:
                            print("It's not a bug - its a feature")
                            print(ray_segment)
                            print(side)
                            print(e)
        
        
            #pygame.display.flip()
        obs = obs / 100
        return obs.reshape((len(obs), 1))

    def update(self):
        self.age += 1
        self._move()
        self._update_mask()


class Environment:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((400, 400))
        pygame.display.set_caption('Car Driving')
        # pygame.mouse.set_visible(0)

        self.background = pygame.Surface(self.screen.get_size())
        self.background = self.background.convert()
        self.background.fill((250, 250, 250))

        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

    def reset(self, car, walls,pedestrians=[]):
        self.car = car
        self.walls = walls
        self.pedestrians = pedestrians
        self.sprites = pygame.sprite.RenderPlain((*self.walls, *self.pedestrians, car))

    def loop(self, action):
        # keep pygame from timing out
        if not bool(pygame.event.peek()):
            e = pygame.event.Event(
                pygame.USEREVENT, some_attr=1, other_attr='1')
            pygame.event.post(e)
        angle, accel = action
        self.car.rotate(angle)
        self.car.accelerate(accel)
        self.car.handle_collisions(self.walls, self.pedestrians)

    def render(self):
        self.sprites.update()
        self.screen.blit(self.background, (0, 0))
        self.sprites.draw(self.screen)
        pygame.display.flip()

    def close(self):
        pygame.quit()


walls_border = [
    Wall(0, 0, 400, 2, 'black'),
    Wall(0, 0, 2, 400, 'black'),
    Wall(0, 398, 400, 2, 'black'),
    Wall(398, 0, 2, 400, 'black')
]

walls_horiz1 = [
    Wall(0, 320, 60, 10, 'black'),
    Wall(120, 320, 80, 10, 'black'),
    Wall(260, 320, 140, 10, 'black')
]

walls_vert12 = [
    Wall(50, 200, 10, 120, 'black'),
    Wall(120, 200, 10, 120, 'black'),
    Wall(190, 200, 10, 120, 'black'),
    Wall(260, 200, 10, 120, 'black')
]

walls_horiz2 = [
    Wall(0, 200, 60, 10, 'black'),
    Wall(120, 200, 80, 10, 'black'),
    Wall(260, 200, 140, 10, 'black'),
    Wall(0, 140, 200, 10, 'black'),
    Wall(260, 140, 60, 10, 'black'),
    Wall(370, 140, 30, 10, 'black'),
]

walls_vert23 = [
    Wall(190, 50, 10, 90, 'black'),
    Wall(260, 80, 10, 60, 'black'),
    Wall(310, 80, 10, 60, 'black'),
    Wall(370, 80, 10, 60, 'black'),
    Wall(140, 50, 10, 30, 'black'),
    Wall(50, 0, 10, 80, 'black')
]

walls_horiz3 = [
    Wall(50, 80, 100, 10, 'black'),
    Wall(150, 50, 40, 10, 'black'),
    Wall(260, 80, 60, 10, 'black'),
    Wall(370, 80, 30, 10, 'black')
]

walls = [*walls_border, *walls_horiz1, *walls_horiz2,
         *walls_horiz3, *walls_vert12, *walls_vert23]


def main():
    env = Environment()
    car = Car((100, 30))
    
    env.reset(car, walls, [ped1,ped2,])
    env.render()

    clock = pygame.time.Clock()
    while True:
        accel = 0
        angle = 0
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT:
                return
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                return
            elif event.type == KEYDOWN and event.key == K_SPACE:
                print('===OBSERVATION===')
                obs, intersections = env.car.observe(env.walls)
                for i, dist in enumerate(obs):
                    print(f"{5*i}: {dist}, Intersects={bool(intersections[i])}")
                print('===END OBSERVATION===')
            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    accel = 0.5
                elif event.key == K_DOWN:
                    accel = -0.5
                elif event.key == K_LEFT:
                    angle = -5
                elif event.key == K_RIGHT:
                    angle = 5
        env.loop((angle, accel))
        env.car.observe(env.walls, env.pedestrians)
        # Comment out
        # print(env.car.reward)
        env.render()


if __name__ == "__main__":
    main()
