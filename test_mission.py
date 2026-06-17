import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import sys

# Monkey-patch to limit mission to 5 steps for testing
original_is_complete = None

def patch_is_complete(self):
    # Mission is "complete" after 5 steps
    if not hasattr(self, '_step_count'):
        self._step_count = 0
    self._step_count += 1
    if self._step_count > 5:
        return True
    return original_is_complete(self) if original_is_complete else False

try:
    print("=" * 60)
    print("MISSION STARTUP TEST")
    print("=" * 60)
    
    from main import create_mission, run_mission, print_final_report
    from src.autonomy.mission_manager import MissionManager
    
    # Patch for quick test
    original_is_complete = MissionManager.is_complete
    MissionManager.is_complete = patch_is_complete
    
    print("\n[1] Creating mission...")
    mission = create_mission()
    print("    ✓ Mission created")
    
    print("[2] Starting mission loop...")
    metrics, battery = run_mission()
    print("    ✓ Mission completed")
    
    print("[3] Generating final report...")
    print_final_report(metrics, battery)
    print("    ✓ Report generated")
    
    print("\n" + "=" * 60)
    print("TEST PASSED - NO CRASHES")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
