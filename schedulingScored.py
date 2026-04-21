from collections import defaultdict

def assign_delivery_days_scored(inst, dist):
    usage = defaultdict(int)
    
    day_load = defaultdict(int)
    
    delivery_day = {}
    
    depot = inst.DepotCoordinate
    
    sorted_requests = sorted(
        inst.Requests,
        key=lambda r: (
            r.toDay - r.fromDay,
            -r.toolCount,
            dist[depot][r.node]
        )
    )
    
    for request in sorted_requests:
        tool = inst.Tools[request.tool - 1]
        tool_id = tool.ID
        tool_max = tool.amount
        
        if tool.weight * request.toolCount > inst.Capacity:
            raise Exception(f"Request {request.ID} cannot be fulfilled: tool weight {tool.weight} x count {request.toolCount} exceeds vehicle capacity {inst.Capacity}")
        
        best_day = None
        best_score = float('inf')
        
        for day in range(request.fromDay, request.toDay + 1):
            pickup_day = day + request.numDays
            
            if pickup_day > inst.Days:
                continue
            
            current_peak = max(
                usage[(d, tool_id)] for d in range(1, inst.Days + 1)
            )
            
            peak_usage = 0
            feasible = True
            
            for d in range(day, pickup_day + 1):
                new_usage = usage[(d, tool_id)] + request.toolCount
                if new_usage > tool_max:
                    feasible = False
                    break
                peak_usage = max(peak_usage, new_usage)
                
            if not feasible:
                continue
            
            new_peak = max(current_peak, peak_usage)
            distance_penalty = dist[depot][request.node]
            
            score = (
                tool.cost * (new_peak - current_peak) +
                2 * (day_load[day] + day_load[pickup_day]) +
                1 * (day - request.fromDay) +
                1 * distance_penalty
            )
            
            if score < best_score:
                best_score = score
                best_day = day
        
        if best_day is None:
                best_day = min(
                    range(request.fromDay, request.toDay + 1),
                    key=lambda day: max(
                        usage[(d, tool_id)]
                        for d in range(day, day + request.numDays + 1)
                    )
                )
            
        if best_day is None:
            raise Exception(f"Could not schedule request {request.ID}")
            
        delivery_day[request.ID] = best_day
        pickup_day = best_day + request.numDays
            
        for d in range(best_day, pickup_day + 1):
            usage[(d, tool_id)] += request.toolCount
            
        day_load[best_day] += 1
        day_load[pickup_day] += 1
        
    print("scheduled", len(delivery_day), "out of", len(inst.Requests))
    missing = [req.ID for req in inst.Requests if req.ID not in delivery_day]
    print("missing:", missing[:20])

    return delivery_day