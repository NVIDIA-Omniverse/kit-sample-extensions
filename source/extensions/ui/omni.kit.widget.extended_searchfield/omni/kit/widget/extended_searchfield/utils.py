# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
from typing import Dict, List

import carb
import omni.client

IMAGE_TYPES = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".tga"]


def find_next_unescaped_quote(word: str, start: int = 0) -> int:
    dquote = word.find('"', start)
    if dquote == -1:
        return -1
    escaped = False
    # an odd number of escaping slashes before the quote means it is escaped.
    for i in reversed(range(dquote)):
        if word[i] != "\\":
            break
        escaped = not escaped
    if escaped:
        return find_next_unescaped_quote(word, dquote + 1)
    else:
        return dquote


def split_with_quotes(value: str) -> List[str]:
    """Split a string at the spaces but preserve quotes. Examples:

    'command1:"Blue car" command2:red car' -> ['command1:"Blue car"', 'command:red', 'car']

    Args:
        value (str): The string to split

    Returns:
        list: List of strings that were split.
    """
    results: List[str] = []
    value = value.strip()

    while value:
        space = value.find(" ")
        if space == -1:
            return results + [value]

        dquote = value.find('"')
        # no quotes or space before quotes
        if (dquote >= 0 and space < dquote) or dquote == -1:
            results.append(value[:space])
            value = value[space + 1 :].strip()
        # found double quote first
        elif dquote >= 0:
            next_dquote = find_next_unescaped_quote(value, dquote + 1)
            if next_dquote >= 0:
                results.append(value[: next_dquote + 1])
                value = value[next_dquote + 1 :].strip()
            else:
                # no 2nd double quote. Take input verbatim.
                results.append(value[:space])
                value = value[space + 1 :].strip()
        else:
            return results + [value]

    return results


def is_omniverse_url(url: str) -> bool:
    broken_url = omni.client.break_url(url)
    return broken_url.scheme == "omniverse"


def has_thumbnail_or_image(path: str) -> bool:
    """Check if the path is an image file or it has a thumbnail in omniverse.

    Image search only works on images. If the file is local it must be an image, otherwise it must either
    be an image or have a valid thumbnail. Thumbnails exist in either of these two locations:
    <omniverse-path>/.thumbs/256x256/<filename-with-extension>.png
    <omniverse-path>/.thumbs/256x256/<filename-with-extension>.auto.png

    Args:
        path (str): Path to the file (local or on omniverse)

    Returns:
        bool: True if there is an image or thumbnail we can search for.
    """
    dirname, full_filename = os.path.split(path)
    if not full_filename:
        return False
    filename, ext = os.path.splitext(full_filename)
    if not filename:
        return False
    if ext.lower() in IMAGE_TYPES:
        return True
    if not is_omniverse_url(path):
        return False

    try:
        result, entry = omni.client.stat(path)
        if result == omni.client.Result.OK and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
            return False

        thumbnail_check = os.path.join(dirname, ".thumbs", "256x256", full_filename + ".auto.png").replace("\\", "/")
        result, _ = omni.client.stat(thumbnail_check)
        if result == omni.client.Result.OK:
            return True

        thumbnail_check = os.path.join(dirname, ".thumbs", "256x256", full_filename + ".png").replace("\\", "/")
        result, _ = omni.client.stat(thumbnail_check)
        if result == omni.client.Result.OK:
            return True
    except BaseException as e:
        carb.log_error(f"Error when checking for thumbnails of {path}: {str(e)}")

    return False


async def get_username(url: str) -> str:
    result, info = await omni.client.get_server_info_async(url)
    return info.username if result == omni.client.Result.OK else ""


def quotify(value: str) -> str:
    """If the string has spaces in it, surround it with quotes.

    Args:
        path (str): The string to check.

    Returns:
        str: The string surrounded by quotes if necessary.
    """
    # strip quotes first to avoid double quoting
    value = remove_quotes(value)
    return f'"{value}"' if " " in value else value


def remove_quotes(text: str) -> str:
    return text.replace('"', "")


def query_to_dict(query: List[str]) -> Dict[str, List[str]]:
    """Convert a list of commands to a dictionary where the key is the prefix (text before a :)
    and the empty string key represents no prefix

    Args:
        query (List[str]): List of search queries

    Returns:
        Dict[str, List[str]]: Dictionary of prefixes and searches
    """
    result = {}
    for word in query:
        c = word.find(":")
        prefix = "" if c == -1 else word[:c]
        if prefix in result:
            result[prefix].append(word)
        else:
            result[prefix] = [word]
    return result


def combine_queries(old_query: List[str], new_query: List[str]) -> List[str]:
    """Combine the old query with the new query.
    - preserve the order of the old_query when possible
    - all new_query words will be in the result, replacing old_query words with the same prefix
    - old_query words without a prefix will remain where they are
    - old_query words with a prefix will be replaced or removed

    Example (Note that the order of the old_query is preserved):
    old_query: ["ext:usd", "car"], new_query: ["tag:blue", "ext:png"], combined: ["ext:png", "car", "tag:blue"]

    Args:
        old_query (List[str]): List of strings which may or may not have prefixes. Strings may be empty.
        new_query (List[str]): List of strings, each containing a prefix. No empty strings.

    Returns:
        List[str]: All of the new query, some of the old (if not overwritten). No empty strings.
    """
    # Create a dictionary of prefix: [word1, word2, word3]
    # For example: ["car", "tag:red", "tag:blue"] -> {"": ["car"], "tag": ["tag:red", "tag:blue"]}
    new_query_dict = query_to_dict(new_query)
    combined_result = []
    processed_prefixes = []
    to_append = []

    # For each word, either append it, overwrite it, or remove it.
    for index, word in enumerate(old_query):
        if not word:
            continue

        c = word.find(":")
        prefix = word[:c] if c > 0 else None

        if not prefix or prefix in processed_prefixes:
            combined_result.append(word)
        elif prefix in new_query_dict:
            new_words = new_query_dict[prefix]
            # overwrite first old word with the new word
            combined_result.append(new_words[0])
            # Go over the rest of the old_query and overwrite or clear the old words.
            # - If len(old) < len(new): append extra new words at the end
            # - If len(old) > len(new): clear extra old words
            new_word_index = 1
            for i in range(index + 1, len(old_query)):
                c = old_query[i].find(":")
                if c > 0 and old_query[i][:c] == prefix:
                    if new_word_index < len(new_words):
                        # this will be copied over to the combined_result later
                        old_query[i] = new_words[new_word_index]
                        new_word_index += 1
                    else:
                        old_query[i] = ""

            to_append += new_words[new_word_index:]
            # Only process each unique prefix once
            processed_prefixes.append(prefix)

    # Add the remaining new terms that did not match anything in the old_query
    for prefix, words in new_query_dict.items():
        if prefix not in processed_prefixes:
            combined_result += words

    return combined_result + to_append
