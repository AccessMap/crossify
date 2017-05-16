# Sidewalkify

`crossify` is a Python library and command line application for drawing
crossings from sidewalk datasets like those produced in 'sidewalkify.

## Introduction

Sidewalk data is often recorded as metadata for street lines,
such as whether a sidewalk is on the left or the right side, and at what
distance. This method of storage is good for questions such as, 'what streets
have sidewalks?', but are not as good for knowing exactly where a sidewalk is
and how it connects to other sidewalks (e.g., places to cross the street,
curb ramps, etc). This package helps to answer where connectivity across sidewalk islands are
by generating best quess crossings at legal locations.
