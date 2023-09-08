
## find_launch_time

Find a good launch time for small-scale stratospheric balloon launches.
Flying balloons which are guided only by the winds requires predictions about the trajectory for a successful recovery to be likely.
This tool outputs polygons which represent the area where the balloon is likely to land.

See https://github.com/jparta/balloon-flights-planner for an example of usage. This tool is used in the scheduled task.

Uses https://github.com/jparta/astra_simulator as trajectory prediction backend.


Here's the launch time suggestion finding algorithm overview:

![find_launch_time_suggestion_algorithm](https://raw.githubusercontent.com/jparta/find_launch_time/master/images/find_launch_time_process.png)
