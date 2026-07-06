"""Kernel loads and the offer is concrete numbers (Day-0 gate, SPEC §5.1)."""

from leadscout.kernel import load_kernel


def test_kernel_loads_and_offer_is_a_number():
    k = load_kernel()
    assert k.icp.vertical
    assert k.icp.geography
    assert k.offer.archetype == "rag_support_bot"
    # offer is a number
    assert "%" in k.offer.headline_number
    assert "$" in k.offer.pilot.price
    assert k.offer.pilot.weeks.strip().isdigit()
    assert len(k.disqualifiers) == 3
    # cost model is present and numeric
    d = k.problem.cost_logic.primary.defaults
    assert d["deflectable_fraction"] > 0
    assert d["loaded_annual_cost_per_rep"] > 0
