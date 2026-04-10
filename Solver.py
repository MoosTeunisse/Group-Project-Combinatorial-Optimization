import sys
from InstanceCVRPTWUI import InstanceCVRPTWUI

def main():
    #You can run this file by typing "python Solver.py "instances 2026\instances\B1.txt"" in the command line
    #of course you can use a different file, the above is just an example.
    
    if len(sys.argv) < 2:
        print("Usage: python Solver.py <instance_file>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    
    instance = InstanceCVRPTWUI(input_path, "txt")
    
    #prints the general info about the instance like the costs and stuff
    print("Instance loaded successfully.")
    print("Dataset:", instance.Dataset)
    print("Name:", instance.Name)
    print("Days:", instance.Days)
    print("Capacity:", instance.Capacity)
    print("Max trip distance:", instance.MaxDistance)
    print("Depot coordinate:", instance.DepotCoordinate)
    print("Vehicle cost:", instance.VehicleCost)
    print("Vehicle day cost:", instance.VehicleDayCost)
    print("Distance cost:", instance.DistanceCost)
    print("Number of tools:", len(instance.Tools))
    print("Number of coordinates:", len(instance.Coordinates))
    print("Number of requests:", len(instance.Requests))
    
    #prints all the info about the first tool
    if instance.Tools:
        t = instance.Tools[0]
        print("First tool details:")
        print("  ID:", t.ID)
        print("  Weight:", t.weight)
        print("  Amount:", t.amount)
        print("  Cost:", t.cost)
    
    #prints all the info about the first request
    if instance.Requests:
        r = instance.Requests[0]
        print("First request details:")
        print("  ID:", r.ID)
        print("  Node:", r.node)
        print("  From day:", r.fromDay)
        print("  To day:", r.toDay)
        print("  Number of days:", r.numDays)
        print("  Tool:", r.tool)
        print("  Tool count:", r.toolCount)

    #prints the coordinates of the first request's node
    if instance.Coordinates:
        c = instance.Coordinates[instance.Requests[0].node]
        print("First coordinate details:")
        print("  ID:", c.ID)
        print("  X:", c.X)
        print("  Y:", c.Y)

if __name__ == "__main__":
    main()
    