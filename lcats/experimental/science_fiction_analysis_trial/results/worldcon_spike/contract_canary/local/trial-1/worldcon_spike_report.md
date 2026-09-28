# Worldcon Knight/Novum Spike Report

- Report version: `worldcon-knight-novum-spike-report-v1`
- Work item: `WI-SF-0015`
- Mode: `canary`
- Backend: `openai-compatible`
- Model: `gpt-oss:20b`
- Status: `failed`
- Stories complete: `1/2`
- Input tokens: `44919`
- Output tokens: `10520`
- Latency seconds: `965.032`

## Go/No-Go Note

Stop/revise: the spike did not complete structurally.

## Stories

### mass_quantities/a_case_of_sunburn__fontenay

- Title: A Case of Sunburn
- Status: `complete`
- Knight interval: `0/0`
- Qualified novum count: `0`
- Dominant novum: `None`
- Sidecar: `experimental/science_fiction_analysis_trial/results/worldcon_spike/contract_canary/local/trial-1/mass_quantities/a_case_of_sunburn__fontenay/science-fiction.json`

### anderson/bell

- Title: Anderson - The Bell
- Status: `failed`
- Knight interval: `None/None`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `None`

- Failure kind: `InternalServerError`
- Failure message: Error code: 500 - {'error': {'message': 'error parsing tool call: raw=\'{"evidence":[{"raw_id":"id1","type":"scientific_or_technical_explanation","quote":"the sound proceeded from a very large owl, in a hollow tree; a sort of learned owl, that continually knocked its head against the branches.","paragraph_ids":["p00004"],"paraphrase":"Explanation attributing bell sound to an owl in a hollow tree.","confidence":0.95},{"raw_id":"id2","type":"inquiry_or_scientific_method","quote":"he got the place of \'Universal Bell-ringer\', and wrote yearly a short treatise \'On the Owl\'; but everybody was just as wise as before.","paragraph_ids":["p00004"],"paraphrase":"Describes authoring a treatise to investigate bell origin.","confidence":0.9},{"raw_id":"id3","type":"character_reaction","quote":"Now we are there! In reality the bell does not exist; it is only a fancy that people have taken into their heads!","paragraph_ids":["p00007"],"paraphrase":"Children express disbelief about the bell\'s existence.","confidence":0.9},{"raw_id":"id4","type":"temporal_or_spatial_displacement","quote":"And he seized hold of the creeping-plants, and the roots of trees—climbed up the moist stones where the water-snakes were writhing…","paragraph_ids":["p00019"],"paraphrase":"King\'s Son climbs higher ground into forest.","confidence":0.85},{"raw_id":"id5","type":"extrapolative_consequence","quote":"I must and will find the bell, even if I am obliged to go to the end of the world.","paragraph_ids":["\', err=unexpected end of JSON input', 'type': 'api_error', 'param': None, 'code': None}}

