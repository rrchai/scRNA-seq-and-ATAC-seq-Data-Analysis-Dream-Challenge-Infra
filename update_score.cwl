#!/usr/bin/env cwl-runner
#
# 1. upload the collected scores to synapse and
# 2. add the scores entity id to annotation
# 3. query all scored submission results
# 4. update a leader board with rankings of the submission
#
cwlVersion: v1.0
class: CommandLineTool
baseCommand: [python3, /update_score.py]

hints:
  DockerRequirement:
    dockerPull: docker.synapse.org/syn26720921/scoring:v1

inputs:
  - id: synapse_config
    type: File
  - id: results
    type: File
  - id: parent_id
    type: string
  - id: all_scores
    type: File

arguments:
  - valueFrom: $(inputs.synapse_config.path)
    prefix: -c
  - valueFrom: $(inputs.parent_id)
    prefix: -o
  - valueFrom: $(inputs.results)
    prefix: -r
  - valueFrom: $(inputs.all_scores.path)
    prefix: -f

requirements:
  - class: InlineJavascriptRequirement

outputs:
  - id: new_results
    type: File
    outputBinding:
      glob: results.json