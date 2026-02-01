from game_engine.logic.project_manager import ProjectManager

class MockPlayer:
    def __init__(self, position, team):
        self.position = position
        self.team = team

class MockGame:
    def __init__(self):
        self.players = [
            MockPlayer('Bottom', 'us'),
            MockPlayer('Right', 'them'),
            MockPlayer('Top', 'us'),
            MockPlayer('Left', 'them')
        ]
        self.declarations = {
            'Bottom': [{'score': 20}],
            'Right': [{'score': 50}]
        }

game = MockGame()
pm = ProjectManager(game)
points = pm.calculate_project_points()
print(f"Points: {points}")
assert points['us'] == 20
assert points['them'] == 50
print("Verification Passed")
