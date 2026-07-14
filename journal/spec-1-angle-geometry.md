# Journal Entry 1 — Teaching the Computer to Measure Angles

## The big goal

We're building a pretend spaceship (just computer code) that has to figure
out where it is in space, using nothing but starlight it can see. Before it
can do anything smart, it needs one basic skill: measuring the angle
between two things it points at. This entry is about building that one
skill.

## What is a "vector" here?

Hold your arms out. Point one arm straight ahead. Point the other arm to
your left. Each arm is a "vector" — just an arrow pointing some direction.
It doesn't say how far the wall is, only which way you're pointing.

A star is exactly like this. From wherever the spaceship is, a star is just
a direction — an arrow from the ship to the star. That's all a vector is
in this piece of the project: a direction, nothing about distance.

## What does "angle between" mean?

Look at your two arms again. They're about 90 degrees apart. That's the
whole idea. We want the computer to take two arrows and tell us how many
degrees (or radians — the science version of degrees) apart they are.

## The exact math

Take two arrows, a and b. First, "multiply and add" their matching parts.
This is called a dot product:

    a · b = (a_x * b_x) + (a_y * b_y) + (a_z * b_z)

Next, a fact from basic triangle geometry (not something we invented — it's
always true for any two arrows):

    a · b = (length of a) * (length of b) * cos(angle between them)

Since we can compute the left side with simple arithmetic, and we can
compute the length of each arrow, we can solve for the angle:

    cos(angle) = (a · b) / (length of a * length of b)
    angle = arccos( that number )

arccos just means "undo the cosine" — like pressing an undo button. That's
the entire equation the computer runs. Nothing hidden.

## What this piece does NOT do (important)

- It does not know what a "star" is. It only ever sees two arrows.
  Something else, built later, looks up a star in a catalog and turns it
  into an arrow before handing it over.
- It does not choose which two things to compare. We — or later code —
  decide that by handing it two specific arrows.
- It does not save or remember anything. Give it two arrows, get back one
  number, and it forgets everything the instant it's done. If we want to
  keep that number, something else has to write it down.
- It only ever compares exactly two arrows at a time, never a whole group.
  With 20 stars, later code calls this same tool 20 times — once per
  star — instead of changing this tool to handle 20 at once.

## How we tested it, and why those specific tests

We didn't test it on real stars yet — real star positions are too
complicated to check by hand right now. Instead we used arrows where we
already know the right answer, by hand:

- Arrow straight ahead and arrow to the left → should be 90 degrees
  (pi/2 radians). Just like your arms.
- The same arrow twice → should be 0 degrees (pointing at the same thing
  twice has no angle between it and itself).
- Two arrows pointing exactly opposite → should be 180 degrees
  (pi radians).
- Swapping the order of the two arrows shouldn't change the answer.
- Making one arrow longer or shorter shouldn't change the answer — only
  direction matters, not length.

If the code passes all five of these obvious, hand-checked cases, we trust
it enough to use later on real star data, which we can't check by hand as
easily.

## Where this fits in the bigger picture

This is brick #1 out of many. Every later piece of the project —
figuring out how a star's position appears to shift as the ship moves,
faking a sky full of stars to test against, and finally solving "where is
the ship right now" — needs to measure an angle between two directions
somewhere inside it. This piece is the one all of those borrow from. It
doesn't do anything fancy by itself; it just has to be completely
correct, because everything else depends on it silently, without
re-checking it.

## What's next

Spec 2: using this same angle tool to measure how much a star seems to
shift when the ship moves — the actual parallax effect used for
navigation.
