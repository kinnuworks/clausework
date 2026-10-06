# Live demo image

This folder is deployment glue written by the human after the run. It is not graded and
changes nothing under `stage-4/`: the image copies the band's stage-4 service as is,
starts it, and loads demo data through the service's own reset endpoint.

Demo sign-in: `ada@example.com` / `correct horse`. The free host sleeps when idle; the
first request may take up to a minute, and bookings reset on restart.
