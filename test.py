from classes.states import State, Region
import _misc

#locations = ["Vermont", "VT", "Not a state"]
#for location in locations:
#    print(_misc.convert_state_name_to_abbrev(location.title().strip()))

print(State('VT').name)
print(Region.NORTHEAST.value)
print(State.VERMONT in Region.NORTHEAST.value)
print(Region.get_region(State.VERMONT))
print(State.from_name('Vermont'))