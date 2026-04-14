# import sys
# from InstanceCVRPTWUI import InstanceCVRPTWUI

# class greedySolutionMaker:

    # def __init__(self, x):
        # self.x=x
        # self.y=x.Requests

"""
=============================================================================
VeRoLog 2017  —  Step 2: Greedy Baseline  +  Step 3: Cost Calculator
=============================================================================

MAPSTRUCTUUR (alles in dezelfde map zetten):
    Solver.py              <-- DIT BESTAND
    baseCVRPTWUI.py         <-- uit de zip, NIET aanpassen
    InstanceCVRPTWUI.py     <-- uit de zip, NIET aanpassen
    Validate.py             <-- uit de zip, NIET aanpassen

GEBRUIK:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
    python Solver.py --batch instances/ solutions/

WAT DOET DIT BESTAND?

  STEP 2 — Greedy Baseline (een geldige oplossing, hoe duur ook):
    2A. Wijs aan elk verzoek de vroegst mogelijke leveringsdag toe
        waarbij de toolbeschikbaarheid gerespecteerd wordt.
        Als dat niet lukt: repareer overtredingen iteratief.
    2B. Stuur voor elke taak één aparte truck: depot -> klant -> depot.
        Één taak per truck = nooit capaciteits- of afstandsproblemen.
    2C. Schrijf het resultaat in het officiële tab-gescheiden formaat.

  STEP 3 — Kostenberekening:
    - VEHICLE_COST      × max voertuigen op één dag
    - VEHICLE_DAY_COST  × totaal voertuig-dagen
    - DISTANCE_COST     × totale reisafstand
    - tool.cost         × piek dagelijks toolgebruik per type
=============================================================================
"""

import math
import os
import sys
import argparse
import subprocess
import random
import copy
from collections import defaultdict

from InstanceCVRPTWUI import InstanceCVRPTWUI


# =============================================================================
# HULPFUNCTIE: afstandsmatrix
# =============================================================================

def build_dist_matrix(inst):
    """
    Bouw een n×n afstandsmatrix op basis van inst.Coordinates.
    Gebruikt vloer van Euclidische afstand, zoals het probleem vereist.
    """
    n    = len(inst.Coordinates)
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        ci = inst.Coordinates[i]
        for j in range(i + 1, n):
            cj = inst.Coordinates[j]
            d  = int(math.floor(math.sqrt(
                (ci.X - cj.X) ** 2 + (ci.Y - cj.Y) ** 2
            )))
            dist[i][j] = d
            dist[j][i] = d
    return dist


# =============================================================================
# STEP 2A — Leveringsdagen toewijzen + repair
# =============================================================================

def assign_delivery_days(inst):
    """
    STEP 2A — Wijs aan elk verzoek de vroegst mogelijke leveringsdag toe
    zodat de toolbeschikbaarheid niet overschreden wordt.

    Fase 1 – Greedy toewijzing:
      - Sorteer verzoeken op vroegste deadline (strengste eerst)
      - Kies de vroegste dag in [fromDay, toDay] die haalbaar is
      - Als geen dag haalbaar is: kies de dag met de laagste piek
        (noodoplossing — kan tijdelijk een overtreding veroorzaken)

    Fase 2 – Repair:
      - Als er nog tooloverschrijdingen zijn (door noodoplossingen),
        verschuif de veroorzakers iteratief naar betere dagen tot
        alle overtredingen weg zijn.

    Validator-definitie toolgebruik:
      Tools tellen als 'buiten depot' van leveringsdag t/m ophaaldag
      inclusief: range(leveringsdag, ophaaldag + 1)

    Geeft terug: dict  verzoek-ID -> leveringsdag
    """
    usage = defaultdict(int)   # (dag, tool_id) -> bezetting
    dd    = {}

    # ── Fase 1: Greedy toewijzing ────────────────────────────────────
    gesorteerd = sorted(inst.Requests,
                        key=lambda r: (r.toDay, r.toDay - r.fromDay))

    for req in gesorteerd:
        tool_max = inst.Tools[req.tool - 1].amount
        gekozen  = None

        for dag in range(req.fromDay, req.toDay + 1):
            bezet = range(dag, dag + req.numDays + 1)   # incl. ophaaldag
            if all(usage[(d, req.tool)] + req.toolCount <= tool_max
                   for d in bezet):
                gekozen = dag
                break

        if gekozen is None:
            # Noodoplossing: dag met laagste piekbezetting
            gekozen = min(
                range(req.fromDay, req.toDay + 1),
                key=lambda dag: max(
                    usage[(d, req.tool)]
                    for d in range(dag, dag + req.numDays + 1)
                )
            )

        dd[req.ID] = gekozen
        for d in range(gekozen, gekozen + req.numDays + 1):
            usage[(d, req.tool)] += req.toolCount

    # ── Fase 2: Repair ───────────────────────────────────────────────
    for _ in range(5000):
        # Zoek alle overtredingen
        overtredingen = {
            (d, t): v
            for (d, t), v in usage.items()
            if v > inst.Tools[t - 1].amount
        }
        if not overtredingen:
            break   # klaar

        # Kies een willekeurige overtreding
        (vdag, vtool), _ = random.choice(list(overtredingen.items()))
        tool_max = inst.Tools[vtool - 1].amount

        # Zoek verzoeken die bijdragen aan deze overtreding
        bijdragers = [
            req for req in inst.Requests
            if req.tool == vtool
            and vdag in range(dd[req.ID], dd[req.ID] + req.numDays + 1)
        ]
        if not bijdragers:
            break

        # Kies een willekeurige bijdrager en probeer hem te verschuiven
        req = random.choice(bijdragers)
        cur = dd[req.ID]

        # Verwijder huidige bijdrage
        for d in range(cur, cur + req.numDays + 1):
            usage[(d, req.tool)] -= req.toolCount

        # Zoek haalbare alternatieve dag
        alternatieven = list(range(req.fromDay, req.toDay + 1))
        random.shuffle(alternatieven)
        gekozen = None

        for dag in alternatieven:
            if all(usage[(d, req.tool)] + req.toolCount <= tool_max
                   for d in range(dag, dag + req.numDays + 1)):
                gekozen = dag
                break

        if gekozen is None:
            # Geen perfecte dag: kies dag met laagste piek
            gekozen = min(
                alternatieven,
                key=lambda dag: max(
                    usage[(d, req.tool)]
                    for d in range(dag, dag + req.numDays + 1)
                )
            )

        dd[req.ID] = gekozen
        for d in range(gekozen, gekozen + req.numDays + 1):
            usage[(d, req.tool)] += req.toolCount

    return dd


# =============================================================================
# STEP 2B — Routes bouwen: één truck per taak
# =============================================================================

def build_routes(inst, deliver_day):
    """
    STEP 2B — Stuur voor elke taak één aparte truck.

    Elke truck rijdt: depot -> klant -> depot
    Route = [0, taak, 0]   waarbij 0 = depot

    Positieve taak (+r) = levering van verzoek r
    Negatieve taak (-r) = ophaling van verzoek r

    Dit is de simpelste oplossing die altijd werkt:
      - Nooit capaciteitsproblemen (één taak per truck)
      - Nooit afstandsproblemen (elke klant is bereikbaar)

    Geeft terug: dict  dag -> lijst van routes
    """
    dag_taken = defaultdict(list)

    for req in inst.Requests:
        lever_dag  = deliver_day[req.ID]
        ophaal_dag = lever_dag + req.numDays

        dag_taken[lever_dag].append(+req.ID)    # levering
        dag_taken[ophaal_dag].append(-req.ID)   # ophaling

    days_routes = {}
    for dag, taken in sorted(dag_taken.items()):
        routes = []
        for taak in taken:
            route = [0, taak, 0]   # depot -> klant -> depot
            routes.append(route)
        days_routes[dag] = routes

    return days_routes


# =============================================================================
# STEP 3 — Kostenberekening
# =============================================================================

def compute_cost(inst, dist, deliver_day, days_routes):
    """
    STEP 3 — Bereken de totale kosten van de oplossing.

    Kostformule (uit het probleem):
        VEHICLE_COST      x  max voertuigen gebruikt op één dag
        VEHICLE_DAY_COST  x  totaal voertuig-dagen (som over alle dagen)
        DISTANCE_COST     x  totale reisafstand
        tool[i].cost      x  piek dagelijks gebruik van tool type i

    Toolgebruik (validator-definitie):
      Tools tellen als buiten-depot van leveringsdag t/m ophaaldag
      inclusief: range(leveringsdag, ophaaldag + 1)

    Geeft terug:
        (max_vehicles, total_vehicle_days, tool_use_list,
         total_distance, total_cost)
    """
    num_tools = len(inst.Tools)

    # ── 1. Dagelijks toolgebruik ─────────────────────────────────────
    dagelijks = defaultdict(lambda: [0] * num_tools)

    for req in inst.Requests:
        ti         = req.tool - 1
        lever_dag  = deliver_day[req.ID]
        ophaal_dag = lever_dag + req.numDays

        for dag in range(lever_dag, ophaal_dag + 1):   # incl. ophaaldag
            dagelijks[dag][ti] += req.toolCount

    # Piek per tooltype
    tool_use = [0] * num_tools
    for gebruik in dagelijks.values():
        for i in range(num_tools):
            tool_use[i] = max(tool_use[i], gebruik[i])

    # ── 2. Voertuigen en afstand ─────────────────────────────────────
    max_vehicles       = 0
    total_vehicle_days = 0
    total_distance     = 0

    for dag, routes in days_routes.items():
        max_vehicles        = max(max_vehicles, len(routes))
        total_vehicle_days += len(routes)

        for route in routes:
            for i in range(len(route) - 1):
                stop_a = route[i]
                stop_b = route[i + 1]

                # 0 = depot, anders klantlocatie van dat verzoek
                node_a = inst.DepotCoordinate if stop_a == 0 \
                         else inst.Requests[abs(stop_a) - 1].node
                node_b = inst.DepotCoordinate if stop_b == 0 \
                         else inst.Requests[abs(stop_b) - 1].node

                total_distance += dist[node_a][node_b]

    # ── 3. Totale kosten ─────────────────────────────────────────────
    total_cost = (
          max_vehicles       * inst.VehicleCost
        + total_vehicle_days * inst.VehicleDayCost
        + total_distance     * inst.DistanceCost
        + sum(tool_use[i] * inst.Tools[i].cost for i in range(num_tools))
    )

    return max_vehicles, total_vehicle_days, tool_use, total_distance, total_cost


# =============================================================================
# STEP 2C — Oplossing schrijven
# =============================================================================

def write_solution(inst, dist, deliver_day, days_routes, output_path):
    """
    STEP 2C — Schrijf de oplossing in het officiële tab-gescheiden formaat.

    Elke route wordt geschreven als:
        voertuignr  R  0  taak  0
    (waarden gescheiden door tabs)

    Geeft de totale kosten terug.
    """
    max_v, vdays, tool_use, afstand, kosten = compute_cost(
        inst, dist, deliver_day, days_routes)

    regels = [
        f"DATASET = {inst.Dataset}",
        f"NAME = {inst.Name}",
        "",
        f"MAX_NUMBER_OF_VEHICLES = {max_v}",
        f"NUMBER_OF_VEHICLE_DAYS = {vdays}",
        f"TOOL_USE = {' '.join(str(t) for t in tool_use)}",
        f"DISTANCE = {afstand}",
        f"COST = {kosten}",
        "",
    ]

    for dag in sorted(days_routes):
        routes = days_routes[dag]
        if not routes:
            continue
        regels.append(f"DAY = {dag}")
        regels.append(f"NUMBER_OF_VEHICLES = {len(routes)}")
        for vi, route in enumerate(routes):
            regels.append(f"{vi + 1}\tR\t" + "\t".join(str(x) for x in route))
        regels.append("")

    uitvoermap = os.path.dirname(output_path)
    if uitvoermap:
        os.makedirs(uitvoermap, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write("\n".join(regels))

    return kosten


# =============================================================================
# HOOFDFUNCTIE
# =============================================================================

def solve(instance_path, output_path, verbose=True):
    """Voer Step 2 en Step 3 uit voor één instantie."""
    inst = InstanceCVRPTWUI(instance_path)
    if not inst.isValid():
        print(f"FOUT: ongeldige instantie {instance_path}")
        for fout in inst.errorReport:
            print(f"  {fout}")
        sys.exit(1)

    inst.calculateDistances()
    dist = build_dist_matrix(inst)

    if verbose:
        print(f"\n{'='*55}")
        print(f"  {os.path.basename(instance_path)}")
        print(f"{'='*55}")
        print(f"  Dagen={inst.Days}  Verzoeken={len(inst.Requests)}"
              f"  Klanten={len(inst.Coordinates)-1}  Tools={len(inst.Tools)}")

    if verbose:
        print("\n  [Step 2A] Leveringsdagen toewijzen (+ repair)...")
    deliver_day = assign_delivery_days(inst)

    if verbose:
        print("  [Step 2B] Routes bouwen (één truck per taak)...")
    days_routes = build_routes(inst, deliver_day)

    if verbose:
        print("  [Step 2C] Oplossing schrijven...")
    kosten = write_solution(inst, dist, deliver_day, days_routes, output_path)

    if verbose:
        max_v, vdays, tool_use, afstand, _ = compute_cost(
            inst, dist, deliver_day, days_routes)
        print(f"\n  ── Kostenopbouw (Step 3) ──────────────────────────")
        print(f"  VEHICLE_COST     x {max_v:>5} = {max_v * inst.VehicleCost:>18,}")
        print(f"  VEHICLE_DAY_COST x {vdays:>5} = {vdays * inst.VehicleDayCost:>18,}")
        print(f"  DISTANCE_COST    x {afstand:>5} = {afstand * inst.DistanceCost:>18,}")
        for i, t in enumerate(inst.Tools):
            print(f"  Tool {t.ID} cost      x {tool_use[i]:>5} = {tool_use[i] * t.cost:>18,}")
        print(f"  {'─'*48}")
        print(f"  TOTALE KOSTEN            = {kosten:>18,}")
        print(f"  Bestand                  : {output_path}")

    return kosten


# =============================================================================
# BATCH
# =============================================================================

def solve_batch(instances_dir, solutions_dir, verbose=True):
    """Los alle .txt-instanties in een map op."""
    os.makedirs(solutions_dir, exist_ok=True)
    bestanden = sorted(f for f in os.listdir(instances_dir) if f.endswith('.txt'))
    if not bestanden:
        print(f"Geen .txt-bestanden in: {instances_dir}")
        return
    resultaten = []
    totaal     = 0
    for b in bestanden:
        k = solve(
            os.path.join(instances_dir, b),
            os.path.join(solutions_dir, b.replace('.txt', '_solution.txt')),
            verbose=verbose
        )
        resultaten.append((b, k))
        totaal += k
    print(f"\n{'='*60}\nOVERZICHT\n{'='*60}")
    for b, k in resultaten:
        print(f"  {b:<45}  {k:>15,}")
    print(f"{'─'*60}\n  Totaal: {totaal:>51,}\n{'='*60}")


# =============================================================================
# VALIDATOR
# =============================================================================

def run_validator(instance_path, solution_path, validator_dir=None):
    """Roep de officiële Validate.py aan."""
    if validator_dir is None:
        validator_dir = os.path.dirname(os.path.abspath(__file__))
    validate_py = os.path.join(validator_dir, 'Validate.py')
    if not os.path.isfile(validate_py):
        print(f"[!] Validate.py niet gevonden in: {validator_dir}")
        return
    print("\n[Validator] Oplossing controleren...")
    r = subprocess.run(
        [sys.executable, validate_py, '-i', instance_path, '-s', solution_path],
        capture_output=True, text=True
    )
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="Solver.py",
        description=(
            "VeRoLog 2017 — Step 2 (Greedy Baseline) + Step 3 (Kosten)\n\n"
            "Voorbeelden:\n"
            "  python Solver.py -i instances/testInstance.txt -o solutions/sol.txt\n"
            "  python Solver.py -i instances/testInstance.txt"
            " -o solutions/sol.txt --validate\n"
            "  python Solver.py --batch instances/ solutions/\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('-i', '--instance',    metavar='BESTAND')
    parser.add_argument('-o', '--output',      metavar='BESTAND')
    parser.add_argument('--batch', nargs=2,    metavar=('INST_MAP', 'OPL_MAP'))
    parser.add_argument('--validate',          action='store_true')
    parser.add_argument('--validator-dir',     metavar='MAP', dest='validator_dir')
    parser.add_argument('--seed', type=int,    default=42)
    parser.add_argument('--quiet',             action='store_true')

    args    = parser.parse_args()
    random.seed(args.seed)
    verbose = not args.quiet

    if args.batch:
        solve_batch(args.batch[0], args.batch[1], verbose=verbose)
    elif args.instance:
        output = args.output or args.instance.replace('.txt', '_solution.txt')
        solve(args.instance, output, verbose=verbose)
        if args.validate:
            run_validator(args.instance, output, args.validator_dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()































