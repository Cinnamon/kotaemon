from difflib import SequenceMatcher


def find_text(search_span, context, min_length=5):
    sentence_list = search_span.split("\n")
    context = context.replace("\n", " ")

    matches = []
    # don't search for small text
    if len(search_span) > min_length:
        for sentence in sentence_list:
            match = SequenceMatcher(
                None, sentence, context, autojunk=False
            ).find_longest_match()
            if match.size > max(len(sentence) * 0.35, min_length):
                matches.append((match.b, match.b + match.size))

    return matches


def find_start_end_phrase(
    start_phrase, end_phrase, context, min_length=5, max_excerpt_length=300
):
    context = context.replace("\n", " ")

    matches = []
    matched_length = 0
    for sentence in [start_phrase, end_phrase]:
        if sentence is None:
            continue

        match = SequenceMatcher(
            None, sentence, context, autojunk=False
        ).find_longest_match()
        if match.size > max(len(sentence) * 0.35, min_length):
            matches.append((match.b, match.b + match.size))
            matched_length += match.size

    # check if second match is before the first match
    if len(matches) == 2 and matches[1][0] < matches[0][0]:
        # if so, keep only the first match
        matches = [matches[0]]

    if matches:
        start_idx = min(start for start, _ in matches)
        end_idx = max(end for _, end in matches)

        # check if the excerpt is too long
        if end_idx - start_idx > max_excerpt_length:
            end_idx = start_idx + max_excerpt_length

        final_match = (start_idx, end_idx)
    else:
        final_match = None

    return final_match, matched_length
