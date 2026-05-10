from InstanceCVRPTWUI import InstanceCVRPTWUI
from greedyBaseline import calculate_all_distances, maker_of_routes, compute_cost
from routingSequential import build_routes_sequential_ex
from routingParallel import build_routes_parallel_regret, build_routes_parallel_regret_two_step
from schedulingScored import assign_delivery_days_scored
from localSearch import strip_depots, add_depots, local_search
import pickle, os, numpy as np, matplotlib.pyplot as plt
       
def main(instance_path):
    inst = InstanceCVRPTWUI(instance_path)

    if not inst.isValid():
        return

    distance = calculate_all_distances(inst)
    delivery_days = assign_delivery_days_scored(inst, distance)
    routes_seqEX = build_routes_sequential_ex(inst, delivery_days, distance)
    routes_parRegret = build_routes_parallel_regret(inst, delivery_days, distance)
    routes_parRegretTwoStep = build_routes_parallel_regret_two_step(inst, delivery_days, distance)
    routes_greedyBaseline = maker_of_routes(inst, delivery_days)

    *_, cost_seqEX = compute_cost(inst, distance, delivery_days, routes_seqEX)
    *_, cost_parRegret = compute_cost(inst, distance, delivery_days, routes_parRegret)
    *_, cost_parRegretTwoStep = compute_cost(inst, distance, delivery_days, routes_parRegretTwoStep)
    *_, cost_greedyBaseline = compute_cost(inst, distance, delivery_days, routes_greedyBaseline)


    local_search_seqEX = local_search(strip_depots(routes_seqEX), inst, distance, max_seconds = 5.0, max_iterations = 5000)
    *_, ls_seqEX_cost = compute_cost(inst, distance, delivery_days, add_depots(local_search_seqEX))
    ls_seqEX_cost = min(ls_seqEX_cost, cost_seqEX)
    local_search_parRegret = local_search(strip_depots(routes_parRegret), inst, distance, max_seconds = 5.0, max_iterations = 5000)
    *_, ls_parRegret_cost = compute_cost(inst, distance, delivery_days, add_depots(local_search_parRegret))
    ls_parRegret_cost = min(ls_parRegret_cost, cost_parRegret)
    local_search_parRegretTwoStep = local_search(strip_depots(routes_parRegretTwoStep), inst, distance, max_seconds = 5.0, max_iterations = 5000)
    *_, ls_parRegretTwoStep_cost = compute_cost(inst, distance, delivery_days, add_depots(local_search_parRegretTwoStep))
    ls_parRegretTwoStep_cost = min(ls_parRegretTwoStep_cost, cost_parRegretTwoStep)
    local_search_greedyBaseline = local_search(strip_depots(routes_greedyBaseline), inst, distance, max_seconds = 5.0, max_iterations = 5000)
    *_, ls_greedyBaseline_cost = compute_cost(inst, distance, delivery_days, add_depots(local_search_greedyBaseline))
    ls_greedyBaseline_cost = min(ls_greedyBaseline_cost, cost_greedyBaseline)

    result = {
        'instance': instance_path,
        'baseline': cost_greedyBaseline,
        'sequential': cost_seqEX,
        'parallel': cost_parRegret,
        'parallelTwoStep': cost_parRegretTwoStep,
        'ls_baseline': ls_greedyBaseline_cost,
        'ls_sequential': ls_seqEX_cost,
        'ls_parallel': ls_parRegret_cost,
        'ls_parallelTwoStep': ls_parRegretTwoStep_cost
    }
    return result

Instances = [
    "instances 2026/instances/challenge_r300d20_1.txt",
    "instances 2026/instances/challenge_r300d20_2.txt",
    "instances 2026/instances/challenge_r300d20_3.txt",
    "instances 2026/instances/challenge_r300d20_4.txt",
    "instances 2026/instances/challenge_r300d20_5.txt",
    "instances 2026/instances/challenge_r500d25_1.txt",
    "instances 2026/instances/challenge_r500d25_2.txt",
    "instances 2026/instances/challenge_r500d25_3.txt",
]

if __name__ == "__main__":
    CACHE = "results_cache.pkl"
    
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as f:
            results = pickle.load(f)
        print("Loaded results from cache.")
    else:
        results = []
        for instance in Instances:
            print(f"Processing {instance}...", flush=True)
            result = main(instance)
            results.append(result)
        with open(CACHE, "wb") as f:
            pickle.dump(results, f)

labels = [r['instance'].split('/')[-1].replace('challenge_', '').replace('.txt', '') for r in results]
seq_pct = [(r['baseline'] - r['sequential']) / r['baseline'] * 100 for r in results]
parRegret_pct = [(r['baseline'] - r['parallel']) / r['baseline'] * 100 for r in results]
parRegretTwoStep_pct = [(r['baseline'] - r['parallelTwoStep']) / r['baseline'] * 100 for r in results]
ls_seq_pct = [(r['baseline'] - r['ls_sequential']) / r['baseline'] * 100 for r in results]
ls_parRegret_pct = [(r['baseline'] - r['ls_parallel']) / r['baseline'] * 100 for r in results]
ls_parRegretTwoStep_pct = [(r['baseline'] - r['ls_parallelTwoStep']) / r['baseline'] * 100 for r in results]
ls_baseline_pct = [(r['baseline'] - r['ls_baseline']) / r['baseline'] * 100 for r in results]

x = np.arange(len(labels))
plt.figure(figsize=(12, 6))
width = 0.13
ax = plt.gca()
ax.set_ylim(0, 80)
plt.bar(x - 2.5*width, ls_baseline_pct, width, label='LS Baseline')
plt.bar(x - 1.5*width, seq_pct, width, label='Sequential')
plt.bar(x - 0.5*width, ls_seq_pct, width, label='LS Sequential')
plt.bar(x + 0.5*width, parRegret_pct, width, label='Parallel Regret')
plt.bar(x + 1.5*width, ls_parRegret_pct, width, label='LS Parallel Regret')
plt.bar(x + 2.5*width, parRegretTwoStep_pct, width, label='Two-Step Regret')
plt.bar(x + 3.5*width, ls_parRegretTwoStep_pct, width, label='LS Two-Step Regret')
plt.xticks(x, labels, rotation=45)
plt.xticks(x, labels, rotation=45)
plt.ylabel('Improvement over Baseline (%)')
plt.title('Cost Improvement over Baseline by Heuristic')
plt.legend()
plt.tight_layout()
plt.savefig("heuristic_comparison.png")