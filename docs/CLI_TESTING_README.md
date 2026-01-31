# CLI Testing Framework - Quick Start Guide

## Overview

The CLI Testing Framework provides a fast, reliable way to test the Baloot game without using a browser. It includes detailed logging, game state inspection, and both interactive and automated testing modes.

## Quick Start

### List Available Scenarios
```bash
python cli_test_runner.py --list-scenarios
```

### Run a Full Game (Automated)
```bash
python cli_test_runner.py --scenario full_game --verbose
```

### Interactive Mode (Manual Control)
```bash
python cli_test_runner.py --interactive
```

### Run Multiple Games for Stress Testing
```bash
python cli_test_runner.py --scenario stress_test --games 10 --quiet
```

### Save Logs to File
```bash
python cli_test_runner.py --scenario full_game --log-file test_output.log --debug
```

## Logging Levels

- `--quiet` or `-q`: Minimal output (only errors and final results)
- Default: Key events (bids, trick winners, scores)
- `--verbose` or `-v`: Detailed events (all plays, validations)
- `--debug` or `-d`: Full game state dumps

## Available Scenarios

- **full_game**: Complete game from start to finish
- **bidding_sun**: Test SUN bidding with strong hands
- **bidding_hokum**: Test HOKUM bidding with strong hands
- **bidding_ashkal**: Test ASHKAL bidding with very strong hands
- **project_four**: Test four-of-a-kind project declaration
- **project_sequence**: Test sequence project declaration
- **project_baloot**: Test Baloot (K+Q of trump) project
- **sawa_test**: Test Sawa functionality
- **double_test**: Test game doubling
- **stress_test**: Run 10 consecutive games
- **edge_all_pass**: Test edge case where all players pass

## Examples

### Test Bidding Logic
```bash
python cli_test_runner.py --scenario bidding_sun --verbose
```

### Test Project Declarations
```bash
python cli_test_runner.py --scenario project_four --debug --log-file projects.log
```

### Performance Testing
```bash
python cli_test_runner.py --scenario full_game --games 100 --quiet
```

### Interactive Testing
```bash
python cli_test_runner.py --interactive --verbose
```
In interactive mode:
- You control Player 0
- Other players are bots
- Step through each turn manually
- See detailed game state after each action

## Benefits Over Browser Testing

✓ **Faster**: No browser overhead, direct game logic testing  
✓ **More Reliable**: No crashes or timeouts  
✓ **Better Debugging**: Detailed logs and state inspection  
✓ **Automated**: Run multiple games unattended  
✓ **Flexible**: Interactive and automated modes  
✓ **Observable**: Multiple log levels and file output  

## Files

- `cli_test_runner.py`: Main CLI test runner
- `game_logger.py`: Logging utility with colored output
- `test_scenarios.py`: Predefined test scenarios

## Tips

1. Use `--verbose` to see all game events
2. Use `--debug` to see full game state dumps
3. Use `--log-file` to save logs for later analysis
4. Use `--quiet` for performance testing
5. Use `--interactive` to manually test specific scenarios
