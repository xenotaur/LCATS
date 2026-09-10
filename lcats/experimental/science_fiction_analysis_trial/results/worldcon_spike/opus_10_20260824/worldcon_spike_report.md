# Worldcon Knight/Novum Spike Report

- Report version: `worldcon-knight-novum-spike-report-v1`
- Work item: `WI-SF-0012`
- Mode: `sample`
- Backend: `anthropic`
- Model: `claude-opus-4-8`
- Status: `failed`
- Stories complete: `8/10`
- Input tokens: `343015`
- Output tokens: `37751`
- Latency seconds: `584.759`

## Go/No-Go Note

Stop/revise: the spike did not complete structurally.

## Stories

### mass_quantities/2_b_r_0_2_b__vonnegut

- Title: 2 B R 0 2 B
- Status: `complete`
- Knight interval: `5/6`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/mass_quantities/2_b_r_0_2_b__vonnegut/science-fiction.json`

### mass_quantities/a_bad_day_for_sales__leiber

- Title: A Bad Day for Sales
- Status: `complete`
- Knight interval: `5/5`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/mass_quantities/a_bad_day_for_sales__leiber/science-fiction.json`

### mass_quantities/a_case_of_sunburn__fontenay

- Title: A Case of Sunburn
- Status: `complete`
- Knight interval: `7/7`
- Qualified novum count: `1`
- Dominant novum: `novum-egg-magnetic-amplifier`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/mass_quantities/a_case_of_sunburn__fontenay/science-fiction.json`

### lovecraft/the_colour_out_of_space

- Title: The Colour out of Space by H. P. Lovecraft
- Status: `failed`
- Knight interval: `None/None`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `None`

- Failure kind: `TruncatedResponseError`
- Failure message: Anthropic response for model 'claude-opus-4-8' was truncated at the max_tokens limit (4096) before the tool_use block for 'record_science_fiction_evidence' finished generating; its input may be incomplete or invalid.

### lovecraft/the_call_of_cthulhu

- Title: The Call of Cthulhu by H. P. Lovecraft
- Status: `failed`
- Knight interval: `None/None`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `None`

- Failure kind: `APIStatusError`
- Failure message: {'type': 'error', 'error': {'details': None, 'type': 'invalid_request_error', 'message': 'Output blocked by content filtering policy'}, 'request_id': 'req_011CeMzGgybapisL7Qx1RUS9'}

### anderson/bell

- Title: Anderson - The Bell
- Status: `complete`
- Knight interval: `0/0`
- Qualified novum count: `0`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/anderson/bell/science-fiction.json`

### chesterton/blue_cross

- Title: Chesterton - The Blue Cross
- Status: `complete`
- Knight interval: `0/1`
- Qualified novum count: `0`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/chesterton/blue_cross/science-fiction.json`

### london/brown_wolf

- Title: London - Brown Wolf
- Status: `complete`
- Knight interval: `0/1`
- Qualified novum count: `0`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/london/brown_wolf/science-fiction.json`

### mass_quantities/eve_s_diary_complete__twain

- Title: Eve's Diary, Complete
- Status: `complete`
- Knight interval: `2/4`
- Qualified novum count: `None`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/mass_quantities/eve_s_diary_complete__twain/science-fiction.json`

### mass_quantities/long_odds__haggard

- Title: Long Odds
- Status: `complete`
- Knight interval: `0/2`
- Qualified novum count: `0`
- Dominant novum: `None`
- Sidecar: `/private/tmp/lcats-worldcon-opus-10-20260824/mass_quantities/long_odds__haggard/science-fiction.json`

