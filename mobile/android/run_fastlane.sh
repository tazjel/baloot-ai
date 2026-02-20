#!/bin/bash
gem install fastlane -v 2.221.1 -NV
fastlane supply init --json_key baloot-play-console.json > fastlane_output.txt 2>&1
