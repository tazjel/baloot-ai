"""
Background timer task for checking game timeouts.
"""
import time
import logging
import traceback

from server.room_manager import room_manager

logger = logging.getLogger(__name__)

TIMER_TASK_STARTED = False


def timer_background_task(sio, room_manager_instance):
    """Background task to check for timeouts in all active games"""
    global TIMER_TASK_STARTED
    import os, threading, sys

    debug_msg = (
        f"PID: {os.getpid()} | Thread: {threading.get_ident()} | "
        f"Module: {__name__} | Flag Addr: {id(TIMER_TASK_STARTED)} | "
        f"Value: {TIMER_TASK_STARTED}\n"
    )

    # Check for duplicate modules
    sock_modules = [k for k in sys.modules.keys() if 'socket_handler' in k]
    debug_msg += f"Loaded Socket Handlers: {sock_modules}\n"

    with open("logs/singleton_debug.log", "a") as f:
        f.write(f"{time.time()} PRE-CHECK: {debug_msg}")

    if TIMER_TASK_STARTED:
        logger.warning(f"Timer Background Task ALREADY RUNNING. Skipping. {debug_msg}")
        with open("logs/singleton_debug.log", "a") as f:
            f.write(f"{time.time()} SKIPPED: {debug_msg}")
        return

    TIMER_TASK_STARTED = True

    with open("logs/singleton_debug.log", "a") as f:
        f.write(f"{time.time()} STARTED: {debug_msg}")

    last_heartbeat = time.time()
    logger.info("Timer Background Task Started")

    # Dedicated Debug Logger
    with open("logs/timer_monitor.log", "w") as f:
        f.write(f"{time.time()} STARTUP\n")

    while True:
        sio.sleep(0.1)  # Check every 0.1 second for smoother timeouts

        now = time.time()
        if now - last_heartbeat > 10:
            logger.info(f"Timer Task Heartbeat. Checking {len(room_manager_instance.games)} games.")
            with open("logs/timer_monitor.log", "a") as f:
                f.write(f"{now} HEARTBEAT {len(room_manager_instance.games)} games\n")
            last_heartbeat = now

        try:
            # Create list of IDs to iterate safely (in case dict changes size)
            room_ids = list(room_manager_instance.games.keys())

            for room_id in room_ids:
                game = room_manager_instance.get_game(room_id)
                if not game:
                    continue

                res = game.check_timeout()
                if res and isinstance(res, dict) and res.get('success'):
                    # Timeout caused an action (Pass or AutoPlay)
                    from server.handlers.game_lifecycle import (
                        broadcast_game_update, handle_bot_turn,
                        save_match_snapshot, auto_restart_round
                    )
                    room_manager.save_game(game)
                    broadcast_game_update(sio, game, room_id)

                    # Trigger Bot if next player is bot
                    handle_bot_turn(sio, game, room_id)

                    # Check finish
                    if game.phase == "FINISHED":
                        save_match_snapshot(game, room_id)
                        sio.start_background_task(auto_restart_round, sio, game, room_id)

        except Exception as e:
            logger.exception(f"Error in timer_background_task: {e}")
            with open("logs/crash.log", "a") as f:
                f.write(f"\n{time.time()} CRASH: {e}\n")
                f.write(traceback.format_exc())
            sio.sleep(5.0)  # Backoff on error
