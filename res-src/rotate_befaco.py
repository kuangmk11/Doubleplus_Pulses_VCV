#!/usr/bin/env python3
"""Make horizontal Befaco toggle frames by rotating the stock vertical ones 90°.

The stock BefacoSwitch (Rampage-style lever) throws up/down. We want left/right so
the routing toggles read "left = Bus A, right = Bus B". Rotating each frame 90°
clockwise about the panel maps the down-lever (frame 0) to the LEFT and the up-lever
(frame 2) to the RIGHT, which matches ROUTE_A=0 (left) / ROUTE_B=2 (right).

Input frames live next to this script (bef_0/1/2.svg, fetched from the Rack repo);
output goes to res/BefacoSwitchHoriz_{0,1,2}.svg. Rotation is done by wrapping the
whole frame in a transform group, so the (complex Illustrator) internals are left
untouched.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 27.99345, 31.5642            # stock frame size
NW, NH = H, W                       # rotated: width/height swap


def rotate(src, dst):
    s = open(src).read()
    i = s.index('<svg')
    j = s.index('>', i)             # attr values hold no '>', so this closes the tag
    head, open_tag, inner_tail = s[:i], s[i:j + 1], s[j + 1:]
    k = inner_tail.rindex('</svg>')
    inner, tail = inner_tail[:k], inner_tail[k:]

    open_tag = re.sub(r'width="[\d.]+px"', f'width="{NW}px"', open_tag)
    open_tag = re.sub(r'height="[\d.]+px"', f'height="{NH}px"', open_tag)
    open_tag = re.sub(r'viewBox="[^"]*"', f'viewBox="0 0 {NW} {NH}"', open_tag)

    # translate(NW,0) rotate(90): (x,y) -> (NW - y, x); maps [0,W]x[0,H] into the
    # new [0,NW]x[0,NH] canvas.
    g_open = f'<g transform="translate({NW},0) rotate(90)">'
    open(dst, 'w').write(head + open_tag + g_open + inner + '</g>' + tail)


def main():
    res = os.path.join(HERE, '..', 'res')
    for n in (0, 1, 2):
        rotate(os.path.join(HERE, f'bef_{n}.svg'),
               os.path.join(res, f'BefacoSwitchHoriz_{n}.svg'))
        print(f'wrote res/BefacoSwitchHoriz_{n}.svg')


if __name__ == '__main__':
    main()
