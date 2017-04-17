# copied from Google example cvrptw_plot.py
# This Python file uses the following encoding: utf-8
# Copyright 2015 Tin Arm Engineering AB
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Capacitated Vehicle Routing Problem with Time Windows (and optional orders).

   This is a sample using the routing library python wrapper to solve a
   CVRPTW problem.
   A description of the problem can be found here:
   http://en.wikipedia.org/wiki/Vehicle_routing_problem.
   The variant which is tackled by this model includes a capacity dimension,
   time windows and optional orders, with a penalty cost if orders are not
   performed.
   To help explore the problem, two classes are provided Customers() and
   Vehicles(): used to randomly locate orders and depots, and to randomly
   generate demands, time-window constraints and vehicles.
   Distances are computed using the Great Circle distances. Distances are in km
   and times in seconds.

   A function for the displaying of the vehicle plan
   display_vehicle_output

   The optimization engine uses local search to improve solutions, first
   solutions being generated using a cheapest addition heuristic.
   Numpy and Matplotlib are required for the problem creation and display.

"""
import os
import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import customers as cu
import vehicles as ve


def discrete_cmap(N, base_cmap=None):
    """
    Create an N-bin discrete colormap from the specified input map
    """
    # Note that if base_cmap is a string or None, you can simply do
    #    return plt.cm.get_cmap(base_cmap, N)
    # The following works for string, None, or a colormap instance:

    base = plt.cm.get_cmap(base_cmap)
    color_list = base(np.linspace(0, 1, N))
    cmap_name = base.name + str(N)
    return base.from_list(cmap_name, color_list, N)


def vehicle_output_string(routing, plan, n, num_custs):
    """
    Return a string displaying the output of the routing instance and
    assignment (plan).

    Args:
        routing (ortools.constraint_solver.pywrapcp.RoutingModel): routing.

        plan (ortools.constraint_solver.pywrapcp.Assignment): the assignment.
    Returns:
        (string) plan_output: describing each vehicle's plan.

        (List) dropped: list of dropped orders.

    """
    dropped = []
    for order in range(routing.Size()):
        if (plan.Value(routing.NextVar(order)) == order):
            dropped.append(str(order))

    capacity_dimension = routing.GetDimensionOrDie("Capacity")
    time_dimension = routing.GetDimensionOrDie("Time")
    plan_output = ''

    for route_number in range(routing.vehicles()):
        order = routing.Start(route_number)
        plan_output += 'Route {0}:'.format(route_number)
        if routing.IsEnd(plan.Value(routing.NextVar(order))):
            plan_output += ' Empty \n'
        else:
            while True:
                load_var = capacity_dimension.CumulVar(order)
                time_var = time_dimension.CumulVar(order)
                plan_output += \
                    " {what} {cust} [{order}] Load({load}) Time({tmin}, {tmax}) -> ".format(
                        cust=(order%n),
                        order = order,
                        what=("Pickup" if order < n else 
                              "Return Pickup" if order >= n and order < 2*n else 
                              "Delivery" if order >= num_custs and order < (num_custs+n) else
                              "Return Delivery" if order < 2*num_custs else
                              "Depot"
                          ),
                        load=plan.Value(load_var),
                        tmin=str(timedelta(seconds=plan.Min(time_var))),
                        tmax=str(timedelta(seconds=plan.Max(time_var))))

                if routing.IsEnd(order):
                    plan_output += ' EndRoute {0}. \n'.format(route_number)
                    break
                order = plan.Value(routing.NextVar(order))
        plan_output += "\n"

    return(plan_output, dropped)


def build_vehicle_route(routing, plan, customers, veh_number):
    """
    Build a route for a vehicle by starting at the strat node and
    continuing to the end node.

    Args:
        routing (ortools.constraint_solver.pywrapcp.RoutingModel): routing.

        plan (ortools.constraint_solver.pywrapcp.Assignment): the assignment.

        customers (Customers): the customers instance.

        veh_number (int): index of the vehicle
    Returns:
        (List) route: indexes of the customers for vehicle veh_number
    """
    veh_used = routing.IsVehicleUsed(plan, veh_number)
    print('Vehicle {0} is used {1}'.format(veh_number, veh_used))
    if veh_used:
        route = []
        node = routing.Start(veh_number)  # Get the starting node index
        route.append(customers.customers[routing.IndexToNode(node)])
        while not routing.IsEnd(node):
            route.append(customers.customers[routing.IndexToNode(node)])
            node = plan.Value(routing.NextVar(node))

        route.append(customers.customers[routing.IndexToNode(node)])
        return route
    else:
        return None


def plot_vehicle_routes(veh_route, ax1, customers, vehicles):
    """
    Plot the vehicle routes on matplotlib axis ax1.

    Args:
        veh_route (dict): a dictionary of routes keyed by vehicle idx.

        ax1 (matplotlib.axes._subplots.AxesSubplot): Matplotlib axes

        customers (Customers): the customers instance.

        vehicles (Vehicles): the vehicles instance.
    """
    veh_used = [v for v in veh_route if veh_route[v] is not None]

    cmap = discrete_cmap(vehicles.number+2, 'nipy_spectral')



    for veh_number in veh_used:

        lats, lons, demands = zip(*[(c.lat, c.lon, c.demand) for c in veh_route[veh_number]])
        lats = np.array(lats)
        lons = np.array(lons)
        pickup_lats, pickup_lons = zip(*[(lats[i],lons[i]) for i in range(0,len(lats)) if demands[i] > 0])
        delivery_lats, delivery_lons = zip(*[(lats[i],lons[i]) for i in range(0,len(lats)) if demands[i] < 0])
        sigil = ['v' if d > 0 else '^' for d in demands]
        s_dep = customers.customers[vehicles.starts[veh_number]]
        s_fin = customers.customers[vehicles.ends[veh_number]]
        ax1.annotate('v({veh}) S @ {node}'.format(
                        veh=veh_number,
                        node=vehicles.starts[veh_number]),
                     xy=(s_dep.lon, s_dep.lat),
                     xytext=(10, 10),
                     xycoords='data',
                     textcoords='offset points',
                     arrowprops=dict(
                        arrowstyle="->",
                        connectionstyle="angle3,angleA=90,angleB=0",
                        shrinkA=0.05),
                     )
        ax1.annotate('v({veh}) F @ {node}'.format(
                        veh=veh_number,
                        node=vehicles.ends[veh_number]),
                     xy=(s_fin.lon, s_fin.lat),
                     xytext=(10, -20),
                     xycoords='data',
                     textcoords='offset points',
                     arrowprops=dict(
                        arrowstyle="->",
                        connectionstyle="angle3,angleA=-90,angleB=0",
                        shrinkA=0.05),
                     )
        #ax1.plot(lons, lats, 'o', mfc=cmap(veh_number+1))
        ax1.plot(pickup_lons, pickup_lats, '^', mfc=cmap(veh_number+1))
        ax1.plot(delivery_lons, delivery_lats, 'v', mfc=cmap(veh_number+1))
        ax1.quiver(lons[:-1], lats[:-1],
                   lons[1:]-lons[:-1], lats[1:]-lats[:-1],
                   scale_units='xy', angles='xy', scale=1,
                   color=cmap(veh_number+1))


import argparse

def main():

    parser = argparse.ArgumentParser(description='Solve the PDPTW for round trips.')
    parser.add_argument('-n,--number', type=int, dest='n',default=100,
                        help='Number of round trip customers to generate')
    parser.add_argument('-v,--vehicles', type=int, dest='v',default=30,
                        help='Number of vehicles')
    parser.add_argument('-d,--depots', type=int, dest='d',default=2,
                        help='Number of depots')
    parser.add_argument('--min-demand', type=int, dest='min_demand',default=1,
                        help='Minimum demand per customer')
    parser.add_argument('--max-demand', type=int, dest='max_demand',default=3,
                        help='Maximum demand per customer')
    parser.add_argument('--min-tw', type=float, dest='min_tw',default=1,
                        help='Minimum time window')
    parser.add_argument('--max-tw', type=float, dest='max_tw',default=3,
                        help='Maximum time window')
    parser.add_argument('--min-cap', type=float, dest='min_cap',default=1,
                        help='Minimum vehicle capacity')
    parser.add_argument('--max-cap', type=float, dest='max_cap',default=3,
                        help='Maximum vehicle capacity')
    parser.add_argument('--box-size', type=float, dest='box_size',default=40,
                        help='Box size (km)')
    parser.add_argument('--load-time', type=int, dest='load_time',default=300,
                        help='Load time/unit of demand (s)')
    parser.add_argument('--return-pu-win', type=int, dest='return_pu_win',default=5,
                        help='size of time window for return pickup (minutes)')
    parser.add_argument('--avg-speed', type=int, dest='avg_speed',default=50,
                        help='Avg speed of vehicles (km/h)')
    parser.add_argument('--earliest-start', type=int, dest='earliest_start',default=8*3600,
                        help='The earliest time for first pickup')

    args = parser.parse_args()

    n = args.n
    num_custs = 2*n
    num_vehicles = args.v

    # Create a set of customer, (and depot) custs.
    customers = cu.Customers(n=n, 
                             min_demand=args.min_demand,
                             max_demand=args.max_demand, 
                             box_size=args.box_size,
                             min_tw=args.min_tw, 
                             max_tw=args.max_tw, 
                             num_depots=args.d,
                             load_time=args.load_time, 
                             return_pu_win=args.return_pu_win,
                             avg_speed=args.avg_speed,
                             earliest_start=args.earliest_start)
    print ('customers created')
    # print(customers.customers)

    # Create callback fns for distances, demands, service and transit-times.
    dist_fn = customers.return_dist_callback()
    print('distance callback done')
    dem_fn = customers.return_dem_callback()
    print('demand callback done')
    serv_time_fn = customers.make_service_time_call_callback()
    transit_time_fn = customers.make_transit_time_callback(speed_kmph=args.avg_speed)

    def tot_time_fn(a, b):
        """
        The time function we want is both transit time and service time.
        """
        st = serv_time_fn(a, b)
        tt = transit_time_fn(a, b)
        # print('from '+str(a)+' to '+str(b) + ' service_time: '+str(st) + ' transit_time: '+str(tt))
        return st + tt

    print('time callbacks done')

    # Create a list of inhomgeneous vehicle capacities as integer units.
    capacity = np.random.random_integers(args.min_cap, args.max_cap, num_vehicles)

    # Create a list of inhomogenious fixed vehicle costs.
    cost = [int(100 + 2 * np.sqrt(c)) for c in capacity]

    # Create a set of vehicles, the number set by the length of capacity.
    vehicles = ve.Vehicles(capacity=capacity, cost=cost)
    print ('vehicles created')


    # no need for following line, as the demandnets to zero
    # assert(customers.get_total_demand() < vehicles.get_total_capacity())

    # Set the starting nodes, and create a callback fn for the starting node.
    start_fn = vehicles.return_starting_callback(customers,
                                                 sameStartFinish=True)

    print('start function set')
    for idx in range(0,n):
        print customers.customers[idx],"->\n\t",customers.customers[idx+num_custs]
        print "RETURN",customers.customers[idx+n],"->\n\t",customers.customers[idx+n+num_custs]

    # Set model parameters
    model_parameters = pywrapcp.RoutingModel.DefaultModelParameters()
    print('got model parameters')

    # The solver parameters can be accessed from the model parameters. For example :
    #   model_parameters.solver_parameters.CopyFrom(
    #       pywrapcp.Solver.DefaultSolverParameters())
    #    model_parameters.solver_parameters.trace_propagation = True


    print('calling routing model')
    print('customers.number '+str(customers.number)) # int number
    print('vehicles.number '+ str(vehicles.number))  # int number
    print('vehicles.starts '+ str(vehicles.starts))  # List of int start depot
    print('vehicles.ends '  + str(vehicles.ends))    # List of int end depot
    print('model_parameters ')
    print(model_parameters )

    # Make the routing model instance.
    routing = pywrapcp.RoutingModel(customers.number,  # int number
                                    vehicles.number,  # int number
                                    vehicles.starts,  # List of int start depot
                                    vehicles.ends,  # List of int end depot
                                    model_parameters)

    parameters = routing.DefaultSearchParameters()
    # Setting first solution heuristic (cheapest addition).
    parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.ALL_UNPERFORMED)
    # Disabling Large Neighborhood Search, (this is the default behaviour)
    parameters.local_search_operators.use_path_lns = False
    parameters.local_search_operators.use_inactive_lns = False
    # Routing: forbids use of TSPOpt neighborhood,
    parameters.local_search_operators.use_tsp_opt = False

    parameters.time_limit_ms = 20 * 60 * 1000  # 20 minutes
    parameters.use_light_propagation = False
    # parameters.log_search = True


    # Set the cost function (distance callback) for each arc, homogeneous for
    # all vehicles.
    routing.SetArcCostEvaluatorOfAllVehicles(dist_fn)

    # Set vehicle costs for each vehicle, not homogeneous.
    for veh in vehicles.vehicles:
        routing.SetFixedCostOfVehicle(veh.cost, int(veh.index))

    # Add a dimension for vehicle capacities
    null_capacity_slack = 0
    routing.AddDimensionWithVehicleCapacity(dem_fn,  # demand callback
                                            null_capacity_slack,
                                            capacity,  # capacity array
                                            True,
                                            "Capacity")
    # Add a dimension for time and a limit on the total time_horizon
    routing.AddDimension(tot_time_fn,  # total time function callback
                         customers.time_horizon,
                         customers.time_horizon,
                         True, # fix start cum to zero
                         "Time")

    time_dimension = routing.GetDimensionOrDie("Time")
    solver = routing.solver()
    allvv = {}
    for cust in customers.customers:
        #
        # here is where I should add pick up and delivery constraints
        #
        #
        # Need to have delivery nodes defined as well as pickup nodes
        #
        # by the way, a Customer cust is a named tuple, with members
        # index, demand, lat, lon, tw_open, tw_close.  Deliveries have
        # negative demand.  Pickups have positive demand.
        if cust.demand > 0:
            # this is a pickup node.
            cust_index = routing.NodeToIndex(cust.index)
            # fixme hack I need to add delivery index to pickups,
            # pickup index to deliveries
            deliv = customers.customers[cust.index+num_custs]
            deliv_index = routing.NodeToIndex(deliv.index)
            # print ('adding same vehicle constraint')
            solver.AddConstraint(
                routing.VehicleVar(cust.index) == routing.VehicleVar(deliv.index))

            # print('adding less than, equal to constraint')
            solver.AddConstraint(
                time_dimension.CumulVar(cust_index) <= time_dimension.CumulVar(deliv_index)
                    )
            routing.AddPickupAndDelivery(cust.index, deliv.index);

            # for all original pickups...
            if cust.index < n:
                ret = customers.customers[cust.index+n]

                # compute negatives
                vvcp = solver.IntVar(0,args.v,'cstatcp%d'%cust.index)
                allvv['cstatcp%d'%cust.index] = vvcp
                vvcn = solver.IntVar(0,2,'cstatcn%d'%cust.index)
                allvv['cstatcn%d'%cust.index] = vvcn
                solver.AddConstraint(
                    routing.VehicleVar(cust.index) == vvcp - vvcn
                )
                vvrp = solver.IntVar(0,args.v,'cstatrp%d'%ret.index)
                allvv['cstatrp%d'%ret.index] = vvrp
                vvrn = solver.IntVar(0,2,'cstatrn%d'%ret.index)
                allvv['cstatrn%d'%ret.index] = vvrn
                solver.AddConstraint(
                    routing.VehicleVar(ret.index) == vvrp - vvrn
                )

                solver.AddConstraint(
                    vvcn == vvrn
                )

        # set the time window constraint for this stop (pickup or delivery)
        if cust.tw_open is not None:
            print('index: '+str(cust.index)
                  +" "
                  +("Pickup" if cust.index < n else 
                    "Return Pickup" if cust.index >= n and cust.index < 2*n else 
                    "Delivery" if cust.index >= num_custs and cust.index < (num_custs+n) else
                    "Return Delivery" if cust.index < 2*num_custs else
                    "Depot")
                  +" "+str(cust.index%n)
                  + ' open: ' +str(cust.tw_open) + 
                  (' ttime({fr}->{to}):{ttime}'.format(
                      fr=routing.NodeToIndex(cust.index),
                      to=routing.NodeToIndex(cust.index+num_custs),
                      ttime=str(timedelta(seconds=transit_time_fn(routing.NodeToIndex(cust.index),
                                                                  routing.NodeToIndex(cust.index+num_custs))))
                  ) if cust.index < 2*n else "")+
                  ' close: '+str(cust.tw_close)+' demand:'+str(cust.demand))
            time_dimension.CumulVar(routing.NodeToIndex(cust.index)).SetRange(
                cust.tw_open.seconds,
                cust.tw_close.seconds)
    """
     To allow the dropping of orders, we add disjunctions to all the customer
    nodes. Each disjunction is a list of 1 index, which allows that customer to
    be active or not, with a penalty if not. The penalty should be larger
    than the cost of servicing that customer, or it will always be dropped!
    """
    # To add disjunctions just to the customers, make a list of non-depots.
    non_depot = set([c.index for c in customers.customers if c.tw_open is not None])
    penalty = 400000000  # The cost for dropping a node from the plan.
    nodes = [routing.AddDisjunction([int(c)], penalty) for c in non_depot]



    # This is how you would implement partial routes if you already knew part
    # of a feasible solution for example:
    # partial = np.random.choice(list(non_depot), size=(4,5), replace=False)

    # routing.CloseModel()
    # partial_list = [partial[0,:].tolist(),
    #                 partial[1,:].tolist(),
    #                 partial[2,:].tolist(),
    #                 partial[3,:].tolist(),
    #                 [],[],[],[]]
    # print(routing.ApplyLocksToAllVehicles(partial_list, False))

    # Solve the problem !
    assignment = routing.SolveWithParameters(parameters)

    # The rest is all optional for saving, printing or plotting the solution.
    if assignment:
        # save the assignment, (Google Protobuf format)
        save_file_base = os.path.realpath(__file__).split('.')[0]
        if routing.WriteAssignment(save_file_base + '_assignment.ass'):
            print('succesfully wrote assignment to file ' +
                  save_file_base + '_assignment.ass')

        print('The Objective Value is {0}'.format(assignment.ObjectiveValue()))

        plan_output, dropped = vehicle_output_string(routing, assignment, n, num_custs)
        print(plan_output)
        print('dropped nodes: ' + ', '.join(dropped))

        for i in range(4*n):
            print 'VV',i,assignment.Value(routing.ActiveVar(i))

        for n in allvv.keys():
            print n,allvv[n].Value() if allvv[n].Bound() else 'Unbound'

        # you could print debug information like this:
        # print(routing.DebugOutputAssignment(assignment, 'Capacity'))

        vehicle_routes = {}
        for veh in range(vehicles.number):
            vehicle_routes[veh] = build_vehicle_route(routing, assignment,
                                                      customers, veh)

        # Plotting of the routes in matplotlib.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        # Plot all the nodes as black dots.
        clon, clat = zip(*[(c.lon, c.lat) for c in customers.customers])
        ax.plot(clon, clat, 'k.')
        # plot the routes as arrows
        plot_vehicle_routes(vehicle_routes, ax, customers, vehicles)
        fig.savefig("test.png",dpi=300)
    else:
        print('No assignment')

if __name__ == '__main__':
    main()
