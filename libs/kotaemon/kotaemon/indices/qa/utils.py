from difflib import SequenceMatcher


def find_text(search_span, context, min_length=5):
    search_span, context = search_span.lower(), context.lower()

    sentence_list = search_span.split("\n")
    context = context.replace("\n", " ")

    matches_span = []
    # don't search for small text
    if len(search_span) > min_length:
        for sentence in sentence_list:
            match_results = SequenceMatcher(
                None,
                sentence,
                context,
                autojunk=False,
            ).get_matching_blocks()

            matched_blocks = []
            for _, start, length in match_results:
                if length > max(len(sentence) * 0.25, min_length):
                    matched_blocks.append((start, start + length))

            if matched_blocks:
                start_index = min(start for start, _ in matched_blocks)
                end_index = max(end for _, end in matched_blocks)
                length = end_index - start_index

                if length > max(len(sentence) * 0.35, min_length):
                    matches_span.append((start_index, end_index))

    if matches_span:
        # merge all matches into one span
        final_span = min(start for start, _ in matches_span), max(
            end for _, end in matches_span
        )
        matches_span = [final_span]

    return matches_span


def find_start_end_phrase(
    start_phrase, end_phrase, context, min_length=5, max_excerpt_length=300
):
    start_phrase, end_phrase = start_phrase.lower(), end_phrase.lower()
    context = context.lower()

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


def replace_think_tag_with_details(text):
    text = text.replace(
        "<think>",
        '<details><summary><span style="color:grey">Thought</span></summary><blockquote>',  # noqa
    )
    text = text.replace("</think>", "</blockquote></details>")
    return text


def strip_think_tag(text):
    if "</think>" in text:
        text = text.split("</think>")[1]
    return text
