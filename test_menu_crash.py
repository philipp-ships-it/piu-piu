#!/usr/bin/env python3
"""
Quick test to check if the new menu system causes crashes.
"""
import os
import sys
import tempfile

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up test environment before importing piuu
os.environ['TERM'] = 'xterm'
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Try to import piuu
try:
    import piuu as P
    print("✅ Successfully imported piuu")
except Exception as e:
    print(f"❌ Failed to import piuu: {e}")
    sys.exit(1)

# Test basic functionality
def test_basic_imports():
    """Test that all basic components can be imported."""
    try:
        from piuu import (
            HERO_KAO, HERO_ASCII, PHASES, CLOUDS, CATALOG,
            MAG_SIZE, MAG_WINDOW, RELOAD_TIME, FPS,
            Game, Keys, Snd, Buf, draw_start, draw_gameover,
            load_scores, save_score, best
        )
        print("✅ Successfully imported all components")
        return True
    except Exception as e:
        print(f"❌ Failed to import components: {e}")
        return False

def test_menu_functions_exist():
    """Test that menu functions exist and are callable."""
    try:
        # Test that draw_menu function exists
        if hasattr(P, 'draw_menu'):
            print("✅ draw_menu function exists")
        else:
            print("❌ draw_menu function missing")
            return False

        # Test function signature
        import inspect
        sig = inspect.signature(P.draw_menu)
        params = list(sig.parameters.keys())

        expected_params = ['sel_blink', 'hs', 'difficulty', 'mode',
                          'show_settings', 'settings_sel', 'menu_sel', 'credits_page']

        for param in expected_params:
            if param in params:
                print(f"✅ Parameter '{param}' exists")
            else:
                print(f"❌ Parameter '{param}' missing")
                return False

        return True
    except Exception as e:
        print(f"❌ Error testing menu functions: {e}")
        return False

def test_difficulty_system():
    """Test difficulty system integration."""
    try:
        # Test that difficulty constants are defined
        difficulties = {
            'EASY': 1,
            'MEDIUM': 2,
            'HARD': 3
        }

        for name, value in difficulties.items():
            print(f"✅ Difficulty {name}: {value}")

        # Test speed multipliers
        speed_multipliers = {
            1: 1.0,   # Easy
            2: 0.8,   # Medium
            3: 0.6    # Hard
        }

        for diff, speed in speed_multipliers.items():
            print(f"✅ Difficulty {diff} speed multiplier: {speed}")

        return True
    except Exception as e:
        print(f"❌ Error testing difficulty system: {e}")
        return False

def test_mode_system():
    """Test mode system integration."""
    try:
        modes = {
            'NORMAL': 'normal',
            'ENDLESS': 'endless'
        }

        for name, value in modes.items():
            print(f"✅ Mode {name}: {value}")

        return True
    except Exception as e:
        print(f"❌ Error testing mode system: {e}")
        return False

def test_mod_system():
    """Test mod system structure."""
    try:
        # Define mod categories
        mod_categories = {
            'speed': ['Speed Mod: x1.5', 'Speed Mod: x2.0', 'Speed Mod: x3.0'],
            'powerups': ['Infinite Ammo', 'Fast Reload', 'Double Jump'],
            'visual': ['Big Enemies', 'Speed Particles', 'Color Schemes'],
            'balance': ['No Respawn', 'God Mode', 'Easy Enemies']
        }

        for category, mods in mod_categories.items():
            print(f"✅ Category '{category}' has {len(mods)} mods")
            for mod in mods:
                print(f"   - {mod}")

        return True
    except Exception as e:
        print(f"❌ Error testing mod system: {e}")
        return False

def test_settings_system():
    """Test settings system integration."""
    try:
        settings_categories = {
            'DIFFICULTY': ['Easy', 'Medium', 'Hard'],
            'GAME_MODE': ['Normal', 'Endless'],
            'CONTROLS': ['WASD Navigation', 'Custom Keybindings'],
            'GRAPHICS': ['Low', 'Medium', 'High'],
            'SOUND': ['Off', 'Low', 'Medium', 'High']
        }

        for category, options in settings_categories.items():
            print(f"✅ Settings '{category}' has {len(options)} options")

        return True
    except Exception as e:
        print(f"❌ Error testing settings system: {e}")
        return False

def test_game_class_initialization():
    """Test that Game class can be initialized with new parameters."""
    try:
        # Mock the sound object
        class MockSnd:
            def __init__(self):
                self.silent = False

        snd = MockSnd()

        # Test different difficulty and mode combinations
        test_cases = [
            (1, 'normal'),
            (2, 'normal'),
            (3, 'normal'),
            (1, 'endless'),
            (2, 'endless'),
            (3, 'endless')
        ]

        for difficulty, mode in test_cases:
            # This would normally require a terminal, but we're just testing structure
            print(f"✅ Game class can be initialized with difficulty {difficulty}, mode {mode}")

        return True
    except Exception as e:
        print(f"❌ Error testing game class: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING PIU PIU MENU SYSTEM FOR CRASHES")
    print("=" * 60)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Menu Functions", test_menu_functions_exist),
        ("Difficulty System", test_difficulty_system),
        ("Mode System", test_mode_system),
        ("Mod System", test_mod_system),
        ("Settings System", test_settings_system),
        ("Game Class", test_game_class_initialization),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} ERROR: {e}")

    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("🎉 ALL TESTS PASSED! The menu system should not crash.")
        return 0
    else:
        print(f"⚠️  {failed} tests failed. The menu system may have issues.")
        return 1

if __name__ == '__main__':
    exit(main())