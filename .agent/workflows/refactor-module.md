---
description: Guide for splitting large Python modules into smaller strategies/components.
---

1. **Analyze Dependencies**
   Identify the class or functions to extract. Check their imports and usages.
   
2. **Create Destination Module**
   Create a new file (e.g., `feature/logic.py`).
   
3. **Move Code**
   Copy the code to the new file. Add necessary imports.
   
4. **Update Original File**
   Delete the moved code from the original file (or delegate).
   Import the new module in the original file.
   
5. **Update References**
   Search for other files importing the original module and update them if necessary.
   
6. **Verify**
   Run linting and tests to ensure no breakages.
