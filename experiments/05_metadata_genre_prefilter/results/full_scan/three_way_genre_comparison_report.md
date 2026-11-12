# Three-way genre evidence comparison

This report compares the existing Gutenberg metadata-rule candidates, Claude Opus `model_detect` assessments, and local `gpt-oss:20b` `model_detect` assessments for the same 146 stories. No source is treated as ground truth; disagreement is evidence for later review, not an adjudication.

## Methodology and limitations

Records are joined by LCATS story ID after strict validation of JSONL structure, duplicate IDs, matching ID sets, model provenance, and distinct source hashes. Genre aliases are normalized to a stable lowercase vocabulary. Multi-label metadata remains an orthogonal flag; its candidate set is used for agreement checks.

## Inputs

- Matched stories: **146**
- Metadata source: `experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`
- Claude Opus source (`claude-opus-4-8`): `experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`
- Local source (`gpt-oss:20b`): `experiments/05_metadata_genre_prefilter/results/full_scan/validation_gpt_oss_20b_http_localhost_11434_v1_results.jsonl`

## Aggregate results

| Category | Count |
| --- | ---: |
| `all_three_agree` | 97 |
| `all_three_differ` | 4 |
| `metadata_local_only` | 8 |
| `metadata_multi_label_models_split` | 2 |
| `metadata_opus_only` | 28 |
| `models_agree_metadata_differs` | 7 |

| Pairwise measure | Count | Rate |
| --- | ---: | ---: |
| `metadata_opus` | 127 | 86.99% |
| `metadata_local` | 107 | 73.29% |
| `models` | 104 | 71.23% |
| `all_three` | 97 | 66.44% |

Metadata multi-label stories: **16** (10.96%).

## Per-metadata-primary genre

| Genre | Stories | Category counts |
| --- | ---: | --- |
| adventure | 6 | `all_three_agree`=5, `metadata_local_only`=1 |
| fantasy | 20 | `all_three_agree`=12, `metadata_opus_only`=8 |
| horror | 20 | `all_three_agree`=19, `metadata_opus_only`=1 |
| humor | 20 | `all_three_agree`=9, `all_three_differ`=2, `metadata_local_only`=1, `metadata_opus_only`=7, `models_agree_metadata_differs`=1 |
| mystery | 20 | `all_three_agree`=14, `metadata_opus_only`=4, `models_agree_metadata_differs`=2 |
| romance | 20 | `all_three_agree`=8, `all_three_differ`=2, `metadata_local_only`=1, `metadata_opus_only`=6, `models_agree_metadata_differs`=3 |
| science fiction | 20 | `all_three_agree`=19, `metadata_local_only`=1 |
| western | 20 | `all_three_agree`=11, `metadata_local_only`=4, `metadata_multi_label_models_split`=2, `metadata_opus_only`=2, `models_agree_metadata_differs`=1 |

## Disagreements

| Story | Metadata candidates | Opus | Local | Category |
| --- | --- | --- | --- | --- |
| `anderson/bell` | fantasy | fantasy | adventure | `metadata_opus_only` |
| `anderson/false_collar` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/fir_tree` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/happy_family` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/leap_frog` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/little_match_girl` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/naughty_boy` | fantasy | fantasy | other | `metadata_opus_only` |
| `anderson/swineherd` | fantasy | fantasy | other | `metadata_opus_only` |
| `chesterton/flying_stars` | mystery | mystery | humor | `metadata_opus_only` |
| `chesterton/honour_of_israel_gow` | mystery | mystery | other | `metadata_opus_only` |
| `chesterton/wrong_shape` | mystery | mystery | horror | `metadata_opus_only` |
| `london/brown_wolf` | western, adventure | adventure | other | `metadata_opus_only` |
| `london/day_s_lodging` | western, adventure | western | adventure | `metadata_multi_label_models_split` |
| `london/sun_dog_trail` | western, adventure | adventure | other | `metadata_opus_only` |
| `london/white_man_s_way` | western, adventure | other | other | `models_agree_metadata_differs` |
| `mass_quantities/a_filbert_is_a_nut__raphael` | science fiction | humor | science fiction | `metadata_local_only` |
| `mass_quantities/a_philanthropist__bacon` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/a_prevaricated_parade__tuttle` | western | humor | western | `metadata_local_only` |
| `mass_quantities/a_reversion_to_type__bacon` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/amy_foster__conrad` | romance | other | romance | `metadata_local_only` |
| `mass_quantities/back_home__davis` | mystery | western | western | `models_agree_metadata_differs` |
| `mass_quantities/bearly_reasonable__tuttle` | western | humor | western | `metadata_local_only` |
| `mass_quantities/brown_john_s_body__marks` | horror | horror | other | `metadata_opus_only` |
| `mass_quantities/creepin_tintypes__tuttle` | western, adventure | humor | western | `metadata_local_only` |
| `mass_quantities/death_and_taxes__hartzell` | romance | humor | fantasy | `all_three_differ` |
| `mass_quantities/dirty_work_for_doughgod__tuttle` | western | humor | western | `metadata_local_only` |
| `mass_quantities/especially_dance_hall_women__ellerbe_ellerbe` | western, romance | romance | western | `metadata_multi_label_models_split` |
| `mass_quantities/eve_s_diary_complete__twain` | humor | humor | fantasy | `metadata_opus_only` |
| `mass_quantities/extracts_from_adam_s_diary_translated_from_the_ori__twain` | humor | humor | fantasy | `metadata_opus_only` |
| `mass_quantities/in_the_valley_of_the_shadow__bacon` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/into_the_blue__austin` | romance | adventure | adventure | `models_agree_metadata_differs` |
| `mass_quantities/julia_the_apostate__bacon` | romance | humor | other | `all_three_differ` |
| `mass_quantities/miss_sarah_jack_of_spanish_town_jamaica__trollope` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/mrs_dud_s_sister__bacon` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/mrs_general_talboys__trollope` | romance | romance | other | `metadata_opus_only` |
| `mass_quantities/mrs_korner_sins_her_mercies__jerome` | romance | humor | humor | `models_agree_metadata_differs` |
| `mass_quantities/my_friend_the_murderer__doyle` | mystery | adventure | adventure | `models_agree_metadata_differs` |
| `mass_quantities/puppet_government__revelle` | humor | science fiction | other | `all_three_differ` |
| `mass_quantities/splashes_of_red__davis` | mystery, romance | mystery | western | `metadata_opus_only` |
| `mass_quantities/the_marriage_of_william_durrant__cummings` | romance | other | other | `models_agree_metadata_differs` |
| `mass_quantities/the_pirate_s_pocket_book__calthrop` | humor | humor | adventure | `metadata_opus_only` |
| `mass_quantities/the_red_fetish__long` | adventure | horror | adventure | `metadata_local_only` |
| `wodehouse/black_for_luck` | humor | romance | other | `all_three_differ` |
| `wodehouse/crowned_heads` | humor | humor | other | `metadata_opus_only` |
| `wodehouse/making_of_mac_s` | humor | romance | humor | `metadata_local_only` |
| `wodehouse/man_with_two_left_feet` | humor | humor | other | `metadata_opus_only` |
| `wodehouse/mixer` | humor | humor | adventure | `metadata_opus_only` |
| `wodehouse/romance_of_an_ugly_policeman` | humor | romance | romance | `models_agree_metadata_differs` |
| `wodehouse/wilton_s_holiday` | humor | humor | other | `metadata_opus_only` |

## Interpretation boundary

These results describe agreement and disagreement among evidence sources. They do not select a ground-truth genre, adjudicate individual stories, or replace the underlying historical evidence files.
