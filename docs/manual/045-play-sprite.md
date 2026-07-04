---
name: PLAY SPRITE
order: 45
token: auto
---


PURPOSE:

To define and control animation for any
of the eight available sprites.

SYNTAX:
```text

PLAY SPRITE spriteNum, startPtr, endPtr,
speed
PLAY SPRITE spriteNum OFF
PLAY SPRITE OFF
```

DESCRIPTION:

Sprite animation is achieved by changing
a sprite’s data pointer to another image
and some defined rate. Each consecutive
image promotes the illusion of motion.

spriteNum (0-7) is the sprite number to
animate.

startPtr (0-255) is the sprites starting
data pointer (first image).

endPtr (0-255) is the sprite’s ending
data pointer (last image).

The start and end pointers represent a
range of consecutive integers where
startPtr < endPtr, however this is not
enforced and will cause incorrect images
to display if violated. The pointer
range should refer to sprite images that
when played from start to end show a
seamless animation. After the last image
is displayed the first image is
displayed again. This occurs
continuously until turned off. See page
64 for details on selecting memory
locations for sprite data.

speed (0-255 jiffies) is the time for
each image to display.

PLAY SPRITE spriteNum OFF will stop
animation for the given sprite.

PLAY SPRITE OFF will stop animation for
all sprites.

EXAMPLE:
```text

10 SPRITE 0,1,6
20 PLAY SPRITE 0, 200,206, 5
30 MOVE 0, 24,50 TO 300,200, 200
40 PLAY SPRITE 0 OFF
```
