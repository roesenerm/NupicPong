#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""A simple client to read Game Events and predict it in real time."""

SECONDS_PER_STEP = 2
WINDOW = 60

# tracks inferences/ predictions
inferences = [0,0,0,0]


try:
    from collections import deque
    import time
    from nupic.data.inference_shifter import InferenceShifter
    from nupic.frameworks.opf.modelfactory import ModelFactory
    import model_params
    import sys
    import random
    import math
    import os
    import getopt
    import pygame
    import numpy as np
    from socket import *
    from pygame.locals import *
    from operator import sub

except ImportError, err:
    print "couldn't load module. %s" % (err)
    sys.exit(2)

def load_png(name):
    """ Load image and return image object"""
    fullname = os.path.join('images', name)
    try:
        image = pygame.image.load(fullname)
        if image.get_alpha is None:
            image = image.convert()
        else:
            image = image.convert_alpha()
    except pygame.error, message:
        print 'Cannot load image:', fullname
        raise SystemExit, message
    return image, image.get_rect()

class Ball(pygame.sprite.Sprite):
    """A ball that will move across the screen"""
    
    def __init__(self, (xy), vector):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = load_png('ball.png')
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.vector = vector
        self.hit = 0
    
    def update(self):
        newpos = self.calcnewpos(self.rect,self.vector)
        self.rect = newpos
        (angle,z) = self.vector
        
        if not self.area.contains(newpos):
            tl = not self.area.collidepoint(newpos.topleft)
            tr = not self.area.collidepoint(newpos.topright)
            bl = not self.area.collidepoint(newpos.bottomleft)
            br = not self.area.collidepoint(newpos.bottomright)
            if tr and tl or (br and bl):
                angle = -angle
                self.runNupic(abs(self.rect[0]))
                self.runNupic(abs(self.rect[1]))
            if tl and bl:
                #self.offcourt()
                "ball hits top and bottom wall, sends coordinates to nupic model"
                angle = math.pi - angle
            if tr and br:
                angle = math.pi - angle
        #self.offcourt()
        else:
            # Deflate the rectangles so you can't catch a ball behind the bat
            player1.rect.inflate(-3, -3)
            player2.rect.inflate(-3, -3)
            
            if self.rect.colliderect(player1.rect) == 1 and not self.hit:
                angle = math.pi - angle
                self.hit = not self.hit
                "ball hits player 1, send coordinates to nupic model"
                self.runNupic(self.rect[0])
                self.runNupic(self.rect[1])
            elif self.rect.colliderect(player2.rect) == 1 and not self.hit:
                angle = math.pi - angle
                self.hit = not self.hit
                "ball hits player 2, send coordinates to nupic model'"
                self.runNupic(self.rect[0])
                self.runNupic(self.rect[1])
    
            elif self.hit:
                self.hit = not self.hit
        self.vector = (angle,z)
    
    def calcnewpos(self,rect,vector):
        (angle,z) = vector
        (dx,dy) = (z*math.cos(angle),z*math.sin(angle))
        return rect.move(dx,dy)

    def runNupic(self, gameEvent):
        # Create the model for predicting Game Event.
        model = ModelFactory.create(model_params.MODEL_PARAMS)
        model.enableInference({'predictedField': 'event'})
        
        # Get the Game Event.
        event = gameEvent
        
        # Run the input through the model.
        modelInput = {'event': event}
        result = model.run(modelInput)
        
        # Update inference.
        inference = result.inferences['multiStepBestPredictions'][1]

        # append inference to inferences list
        inferences.append(int(inference))



class playerAI(pygame.sprite.Sprite):
    
    def __init__(self, side):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = load_png('paddle.png')
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.side = side
        self.speed = 10
        self.state = "still"
        self.reinit()
    
    def reinit(self):
        self.state = "still"
        self.movepos = [0,0]
        if self.side == "left":
            self.rect.midleft = self.area.midleft
        elif self.side == "right":
            self.rect.midright = self.area.midright

    def update(self):
        
        "send predicted coordinates to new position"
        newpos = pygame.Rect(616,inferences[-1], 24, 64)
        
        "if coordinates in area of game screen, display coordinates to screen"
        if self.area.contains(newpos):
            self.rect = newpos
            print 'predicted coordinates', self.rect
        else:
            print 'position not in screen area', newpos
        
        pygame.event.pump()

    def moveInference(self):
        self.movepos = inferences[-2:]


class Bat(pygame.sprite.Sprite):
    """ Movable pong paddle/bat """
    
    def __init__(self, side):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = load_png('paddle.png')
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.side = side
        self.speed = 10
        self.state = "still"
        self.reinit()
    
    def reinit(self):
        self.state = "still"
        self.movepos = [0,0]
        if self.side == "left":
            self.rect.midleft = self.area.midleft
        elif self.side == "right":
            self.rect.midright = self.area.midright
    
    def update(self):
        newpos = self.rect.move(self.movepos)
        
        if self.area.contains(newpos):
            self.rect = newpos
    
        pygame.event.pump()
    
    def moveup(self):
        self.movepos[1] = self.movepos[1] - (self.speed)
        self.state = "moveup"
    
    def movedown(self):
        self.movepos[1] = self.movepos[1] + (self.speed)
        self.state = "movedown"



def main():
    # Initialise screen
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('Nupic Pong')
    
    # Fill background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((0, 0, 0))
    
    # Initialise players
    global player1
    global player2
    player1 = Bat("left")
    player2 = playerAI('right')
    
    # Initialise ball
    speed = 4
    rand = ((0.1 * (random.randint(5,8))))
    ball = Ball((0,0),(rand,speed))
    
    # Initialise sprites
    playersprites = pygame.sprite.RenderPlain((player1, player2))
    ballsprite = pygame.sprite.RenderPlain(ball)
    
    # Blit everything to the screen
    screen.blit(background, (0, 0))
    pygame.display.flip()
    
    # Initialise clock
    clock = pygame.time.Clock()
    
    
    
    # Event loop
    while 1:
        # Make sure game doesn't run at more than 60 frames per second
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                return
            elif event.type == KEYDOWN:
                if event.key == K_a:
                    player1.moveup()
                if event.key == K_z:
                    player1.movedown()
            elif event.type == KEYUP:
                if event.key == K_a or event.key == K_z:
                    player1.movepos = [0,0]
                    player1.state = "still"
                if event.key == K_q or event.key == K_ESCAPE:
                    return
    

        screen.blit(background, ball.rect, ball.rect)
        screen.blit(background, player1.rect, player1.rect)
        screen.blit(background, player2.rect, player2.rect)
        ballsprite.update()
        playersprites.update()
        ballsprite.draw(screen)
        playersprites.draw(screen)
        pygame.display.flip()


if __name__ == '__main__': main()
