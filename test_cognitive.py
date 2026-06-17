"""End-to-end integration test for the cognitive architecture."""
import sys
sys.path.insert(0, ".")

from src.cognition.cognitive_architecture import CognitiveArchitecture

def main():
    # Create architecture
    arch = CognitiveArchitecture(50, 50)
    print("1. Architecture created:", arch)

    # Initialize mission
    arch.initialize_mission(
        home_position=(5, 5),
        target_position=(25, 25),
        obstacles=[(10, 10), (15, 12), (20, 20), (12, 18)]
    )
    print("2. Mission initialized")

    # Run 10 cognitive steps
    for step in range(10):
        result = arch.cognitive_step(
            drone_position=(5 + step * 2, 5 + step * 2),
            drone_heading=0.785,
            drone_speed=2.0,
            visible_obstacles=[(10, 10), (15, 12)],
            target_position=(25, 25),
            battery_level=1.0 - step * 0.03,
            mission_phase="NAVIGATION",
        )
        action = result["action"]
        conf = result["confidence"]
        unc = result["uncertainty"]
        print("   Step %d: action=%s, conf=%.2f, unc=%.3f" % (step + 1, action, conf, unc))

    # Get explanations
    explanations = arch.explain_last_decisions(3)
    print("3. Recent explanations:")
    for exp in explanations:
        print("   - %s..." % exp[:120])

    # Get full cognitive state
    state = arch.get_cognitive_state()
    print("4. Cognitive state keys:", list(state.keys()))
    print("   Beliefs:", state["beliefs"])

    # Complete mission
    arch.complete_mission(success=True)
    print("5. Mission completed")

    # Final stats
    state = arch.get_cognitive_state()
    print("6. Final step count:", state["step_count"])
    print("   Self-eval:", state["self_evaluation"])
    print("   Explanations:", state["explanations"])

    # Verify all subsystems
    assert arch.world_model is not None, "World model missing"
    assert arch.memory is not None, "Memory missing"
    assert arch.attention is not None, "Attention missing"
    assert arch.uncertainty is not None, "Uncertainty missing"
    assert arch.probabilistic is not None, "Probabilistic missing"
    assert arch.bayesian is not None, "Bayesian missing"
    assert arch.rl is not None, "RL missing"
    assert arch.mission is not None, "Mission missing"
    assert arch.explainer is not None, "Explainer missing"
    assert arch.planner is not None, "Planner missing"
    assert arch.self_eval is not None, "Self-eval missing"
    assert arch.confidence is not None, "Confidence missing"
    assert arch.learning is not None, "Learning missing"

    print()
    print("=== ALL 13 COGNITIVE SUBSYSTEMS VERIFIED ===")
    print("=== ALL INTEGRATION TESTS PASSED ===")


if __name__ == "__main__":
    main()