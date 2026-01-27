import os

file_path = "c:\\Users\\MiEXCITE\\Downloads\\py4web\\examples\\react-py4web\\game_logic.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Target Block Start (Line 1469 approx)
start_marker = "                  if self.game_mode == 'HOKUM':"
# Target Block End (Line 1489 approx)
end_marker = "game_points_them = calc_sun(total_abnat_them)"

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    clean_line = line.strip()
    if clean_line == "if self.game_mode == 'HOKUM':":
        start_idx = i
    if clean_line == "game_points_them = calc_sun(total_abnat_them)" and start_idx != -1:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found block: {start_idx} to {end_idx}")
    
    new_logic = """                  # Separate Ardh from Card points for calculation
                  ardh_us = last_trick_bonus['us']
                  ardh_them = last_trick_bonus['them']
                  
                  # Currently card_abnat_us INCLUDES Ardh. We need pure card points.
                  pure_card_us = card_abnat_us - ardh_us
                  pure_card_them = card_abnat_them - ardh_them
                  
                  gp_result = self.calculate_game_points_with_tiebreak(
                      pure_card_us, pure_card_them,
                      ardh_us, ardh_them,
                      bidder_team
                  )
                  
                  game_points_us = gp_result['game_points']['us']
                  game_points_them = gp_result['game_points']['them']
                  winner_team = gp_result['winner']
                  
                  # Add Project Game Points
                  if self.game_mode == 'SUN':
                       proj_gp_us = (project_abnat_us * 2) // 10
                       proj_gp_them = (project_abnat_them * 2) // 10
                  else:
                       proj_gp_us = project_abnat_us // 10
                       proj_gp_them = project_abnat_them // 10
                  
                  game_points_us += proj_gp_us
                  game_points_them += proj_gp_them
                  
                  # Save results for UI
                  self.past_round_results = {
                    'us': {
                        'aklat': pure_card_us,
                        'ardh': ardh_us,
                        'mashaari': project_abnat_us,
                        'abnat': card_abnat_us + project_abnat_us, # Raw Total
                        'result': game_points_us,
                        'projects': winning_projects_us
                    },
                    'them': {
                        'aklat': pure_card_them,
                        'ardh': ardh_them,
                        'mashaari': project_abnat_them,
                        'abnat': card_abnat_them + project_abnat_them, # Raw Total
                        'result': game_points_them,
                        'projects': winning_projects_them
                    },
                    'winner': winner_team,
                    'bidder': self.bidding_player.position if self.bidding_player else None,
                    'gameMode': self.game_mode,
                    'doubling': self.doubling_level
                  }
"""
    
    # We need to remove the "elif self.game_mode == 'SUN':" part too, which is included in the range up to end_marker
    
    # Remove old lines
    del lines[start_idx:end_idx+1]
    
    # Insert new lines
    lines.insert(start_idx, new_logic)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print("Successfully patched game_logic.py")
else:
    print("Could not find target block.")
    # Debug print lines around expected area
    print("Debugging lines 1460-1500:")
    for i in range(1460, min(1500, len(lines))):
         print(f"{i}: {lines[i].rstrip()}")
