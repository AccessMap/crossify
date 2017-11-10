## Alternative strategies

### Select all sidewalks within X meters of the intersection

1. Select all sidewalks within X meters of the intersection
2.

### By studying 'eye test' method

Humans can figure out where to draw crossings pretty easily (even unmarked
ones). How do they do it? Here's some guesses.

1. Locate sidewalk corners. This might be just one sidewalk approaching the
street, it may be a legit corner with 2 sidewalks meeting.

2. If you could reasonably cross from corner to corner, draw a crossing.

3. The location where the crossing connects to the sidewalk is somewhat
subjective and up to the style of the mapper (for now). A natural place is
along the line of the incoming sidewalk, if there are 2. Having them meet at
just one location is *fine* for now.

So, the real strategy in code:

1. Go up the street from the intersection X meters / half way up (whichever
comes first). X could be ~10-15 meters. Return this point for each outgoing
road.

2.

### Original-ish

1. Go up each street in small increments (~half meter?), generating long
orthogonal lines.

2. Restrict to sidewalks within X meters of the street (something moderately
big like 30 meters)

3. Discard lines that don't intersect sidewalks on both the left and right
sides. Can be done by taking the intersection and asking the left/right question

4. Subset remainder to line segment that intersects the street (trim by the
sidewalks)

5. Remove crossings that intersect any other streets (i.e. crossing multiple
streets). This should be done very carefully given that some streets are
divided and have multiple intersections. osmnx tries to group these intersections
but I don't know what happens to the lines. i.e. we don't want to discard all
boulevards. Actual question is more complex? FIXME: revisit this step

6. The first crossing remaining is probably legit.

FIXME: the problem with this approach is that it will miss the situation where
there's only one sidewalk at the corner (one street doesn't have sidewalks,
e.g.).

### Original-ish 2

1. Identify sidewalks to the left of street, to the right of street
2. Find point on the street where an orthogonal line first intersects the
sidewalk on the right and does not intersect any other streets.
3. Repeat for the left side
4. Whichever is farther down is the primary candidate.
5. Attempt to extend this orthogonal line such that it spans from right sidewalk
to left sidewalk.
6. If this fails, find the closest point on the 'other' sidewalk to the point
on the street. Draw a line from sidewalk to sidewalk.

### Original-ish 3: ding ding ding!

1. Walk down the street in X increments.
2. Find a line between the street point and the nearest sidewalk to the right
that does not intersect another street. One method for doing this is to
split the sidewalks up by block beforehand. Alternatively, use the 'block graph'
method used in sidewalkify to group sidewalks. Cyclic subgraphs = block
polygons, acyclic sugraphs = tricky
3. Repeat for the left side.
4. Compare the lines: if they're roughly parallel, keep the crossing endpoints
and draw a line between them. This is the crossing
5. If the crossing is too long (40 meters?), delete it.

Note: rather than incrementing by small amounts and then stopping, this
strategy could use a binary search such that an arbitrary parallel-ness could
be found.
