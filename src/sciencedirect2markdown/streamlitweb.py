import os
import re
import json
from lxml import etree

from sciencedirect2markdown.glyph_match import glyph_match

import streamlit as st

attachment_lookup = {}
floats = {}
processed_floats = set()


def json_to_markdown(data):
    """
    Converts the given JSON data to Markdown.

    Args:
        data: The JSON data to convert.

    Returns:
        The Markdown string.
    """
    global attachment_lookup
    global floats
    global processed_floats

    markdown_output = ""
    processed_floats = set()

    # Create a lookup dictionary for attachment-eid based on file-basename
    if "attachments" in data:
        for attachment in data["attachments"]:
            if "file-basename" in attachment and "attachment-eid" in attachment:
                file_basename = attachment["file-basename"]
                if file_basename not in attachment_lookup:
                    attachment_lookup[file_basename] = attachment["attachment-eid"]
                else:
                    if (
                        "attachment-type" in attachment
                        and attachment["attachment-type"] != "IMAGE-THUMBNAIL"
                    ):
                        attachment_lookup[file_basename] = attachment["attachment-eid"]

    # float
    if "floats" in data:
        for float_item in data["floats"]:
            if "$" in float_item and "id" in float_item["$"]:
                float_id = float_item["$"]["id"]
                floats[float_id] = float_item

    if isinstance(data, dict):
        if "#name" in data:
            tag_name = data["#name"]

            if tag_name == "para":
                markdown_output += handle_para(data)
            elif tag_name == "list":
                markdown_output += handle_list(data)
            elif tag_name == "math":
                markdown_output += handle_math(data)
            elif tag_name == "figure":
                markdown_output += handle_figure(data)
            elif tag_name == "table":
                markdown_output += handle_table(data)
            elif tag_name == "outline":
                markdown_output += handle_outline(data)
            elif tag_name == "sections" or tag_name == "body":
                markdown_output += handle_label(data)
            elif tag_name == "section":
                markdown_output += handle_section(data)
            elif tag_name == "section-title":
                markdown_output += handle_section_title(data)
            elif tag_name == "simple-para":
                markdown_output += handle_simple_para(data)
            elif tag_name == "br":
                markdown_output += handle_br(data)
            elif tag_name == "bold":
                markdown_output += handle_bold(data)
            elif tag_name == "italic":
                markdown_output += handle_italic(data)
            elif tag_name == "small-caps":
                markdown_output += handle_small_caps(data)
            elif tag_name == "sup":
                markdown_output += handle_sup(data)
            elif tag_name == "inf":
                markdown_output += handle_inf(data)
            elif tag_name == "hsp":
                markdown_output += handle_hsp(data)
            elif tag_name == "formula":
                markdown_output += handle_formula(data)
            elif tag_name == "glyph":
                markdown_output += handle_glyph(data)
            elif tag_name == "label":
                markdown_output += handle_label(data)
            elif tag_name == "cross-ref":
                markdown_output += handle_cross_ref(data)
            elif tag_name == "inter-ref":
                markdown_output += handle_inter_ref(data)
            elif tag_name == "intra-ref":
                markdown_output += handle_intra_ref(data)
            elif tag_name == "display":
                markdown_output += handle_display(data)
            elif tag_name == "textbox":
                markdown_output += handle_textbox(data)
            elif tag_name == "caption":
                markdown_output += handle_caption(data)
            elif tag_name == "textbox-body":
                markdown_output += handle_textbox_body(data)
            elif tag_name == "chem":
                markdown_output += handle_label(data)
            elif tag_name == "inline-figure":
                markdown_output += handle_inline_figure(data)
            elif tag_name == "link":
                markdown_output += handle_link(data)
            elif tag_name == "__text__":
                markdown_output += handle_label(data)
            elif tag_name == "acknowledgment" or tag_name == "conflict-of-interest":
                markdown_output += handle_label(data)
            else:
                markdown_output += handle_label(data)
                print(f"Unhandled tag: {tag_name} - {data}")

        elif "content" in data:
            markdown_output += json_to_markdown(data["content"])
        elif "floats" in data:
            markdown_output += json_to_markdown(data["floats"])
        # elif "attachments" in data:
        #     markdown_output += json_to_markdown(data["attachments"])

    elif isinstance(data, list):
        for item in data:
            markdown_output += json_to_markdown(item)

    markdown_output = handle_post_process(markdown_output)

    return markdown_output


def handle_sections(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    return markdown_output


def handle_para(data):
    global processed_floats
    markdown_output = ""
    float_content = ""
    if "_" in data:
        markdown_output += handle_label(data)
    if "$$" in data:
        for item in data["$$"]:
            if item["#name"] == "float-anchor":
                float_id = item["$"]["refid"]
                if float_id not in processed_floats:
                    if float_id in floats:
                        float_data = floats[float_id]
                        if float_data["#name"] == "figure":
                            float_content += handle_figure(float_data)
                        elif float_data["#name"] == "table":
                            float_content += handle_table(float_data)
                        processed_floats.add(float_id)
            else:
                markdown_output += json_to_markdown(item)

    markdown_output += "\n\n" + float_content
    return markdown_output


def handle_simple_para(data):
    markdown_output = ""
    if "_" in data:
        markdown_output += handle_label(data)
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    markdown_output += "\n\n"
    return markdown_output


def handle_list(data, level=0):
    markdown_output = "\n"
    current_level = level
    if "$$" in data:
        for item in data["$$"]:
            if item.get("#name") == "section-title":
                markdown_output += handle_section_title(item)

            if item.get("#name") == "list-item":
                if "$$" in item:
                    label = None
                    content = None
                    nested_content = ""

                    # First pass - get label, content and nested lists
                    for subitem in item["$$"]:
                        if subitem.get("#name") == "label":
                            label = handle_label(subitem)
                        elif subitem.get("#name") == "para":
                            content = handle_para(subitem).strip()
                        elif subitem.get("#name") == "list":
                            nested_content = handle_list(subitem, current_level + 1)

                    # Format the list item with proper indentation
                    if label:
                        if label[-1] == "." and label[:-1].isdigit():
                            # Ordered list item
                            markdown_output += (
                                "    " * current_level + f"{label} {content}\n"
                            )
                        else:
                            # Unordered list item
                            markdown_output += (
                                "    " * current_level + f"- {label} {content}\n"
                            )
                    else:
                        markdown_output += "    " * current_level + f"- {content}\n"

                    # Add any nested content
                    if nested_content:
                        markdown_output += nested_content

            elif item.get("#name") == "list":
                markdown_output += handle_list(item, level + 1)

    markdown_output += "\n"

    return markdown_output


def mathml2latex_yarosh(equation):
    """MathML to LaTeX conversion with XSLT from Vasil Yaroshevich"""
    xslt_file = os.path.join("mathconverter", "xsl_yarosh", "mmltex.xsl")
    dom = etree.fromstring(equation)
    xslt = etree.parse(xslt_file)
    transform = etree.XSLT(xslt)
    newdom = transform(dom)
    return newdom


def mathml2latex_transpect(equation):
    """MathML to LaTeX conversion with XSLT from Transpect"""
    xslt_file = os.path.join("mathconverter", "xsl_transpect", "xsl", "mml2tex.xsl")
    dom = etree.fromstring(equation)
    xslt = etree.parse(xslt_file)
    transform = etree.XSLT(xslt)
    newdom = transform(dom)
    return newdom


def handle_math(data):
    if not ("$$" in data and isinstance(data["$$"], list)):
        return ""

    mathml_content = convert_json_to_mathml(data)

    latex_string = mathml2latex_yarosh(mathml_content)

    return f"${latex_string}$"


def convert_json_to_mathml(data):
    """Converts the math part of JSON data to MathML."""
    if isinstance(data, dict):
        if "#name" in data:
            tag_name = data["#name"]
            if tag_name == "math":
                mathml_string = "<math"
                mathml_string += """ xmlns="http://www.w3.org/1998/Math/MathML" """
                if "$" in data:
                    for attr, value in data["$"].items():
                        mathml_string += f'{attr}="{value}" '
                mathml_string = mathml_string.strip()
                mathml_string += ">"
                if "$$" in data:
                    mathml_string += convert_json_to_mathml(data["$$"])
                mathml_string += "</math>"
                return mathml_string
            else:
                mathml_string = f"<{tag_name}"
                if "$" in data:
                    for attr, value in data["$"].items():
                        mathml_string += f' {attr}="{value}"'
                mathml_string += ">"
                if "_" in data:
                    mathml_string += handle_label(data)
                if "$$" in data:
                    mathml_string += convert_json_to_mathml(data["$$"])
                mathml_string += f"</{tag_name}>"
                return mathml_string
        else:
            return ""
    elif isinstance(data, list):
        mathml_string = ""
        for item in data:
            mathml_string += convert_json_to_mathml(item)
        return mathml_string
    else:
        return str(data)


def handle_figure(data):
    global attachment_lookup
    markdown_output = ""
    caption = ""
    image_url = ""
    label = ""

    if "$$" in data:
        for item in data["$$"]:
            if item["#name"] == "label":
                label = handle_label(item)
            if item["#name"] == "caption":
                caption = handle_caption(item).strip()
            elif item["#name"] == "link":
                if "$" in item and "locator" in item["$"]:
                    locator = item["$"]["locator"]
                    attachment_eid = attachment_lookup.get(locator)
                    if attachment_eid:
                        image_url = construct_image_url(attachment_eid)

    if image_url:
        markdown_output += f"![{label + "." if label else ''}{' ' + caption if caption else ''}]({image_url})\n\n"
        if caption or label:
            markdown_output += f"*{label + "." if label else ''}{' ' + caption if caption else ''}*\n\n"

    return markdown_output


def handle_table(data):
    markdown_output = ""
    caption = ""
    label = ""
    source = ""

    if "$$" in data:
        for item in data["$$"]:
            if item["#name"] == "label":
                label = handle_label(item)
            elif item["#name"] == "caption":
                caption = handle_caption(item).strip()
            elif item["#name"] == "source":
                source = handle_label(item)
            elif item["#name"] == "tgroup":
                markdown_output += handle_tgroup(item)

    if caption or label:
        markdown_output = (
            f"{'**' + label + '**:' if label else ''}{' ' + caption if caption else ''}\n\n"
            + markdown_output
        )
    if source:
        markdown_output += f"\nSource: {source}\n\n---\n\n"
    return markdown_output


def handle_tgroup(data):
    markdown_output = ""
    if "$$" in data:
        num_cols = int(data["$"]["cols"]) if "$" in data and "cols" in data["$"] else 0
        col_widths = []
        header = []
        rows = []

        for item in data["$$"]:
            if item["#name"] == "colspec":
                # You might want to extract col width info here
                col_widths.append(1)  # Default width
            elif item["#name"] == "thead":
                header = handle_thead(item)
            elif item["#name"] == "tbody":
                rows = handle_tbody(item)

        if header:
            markdown_output += "|"
            for i in range(len(header)):
                markdown_output += header[i] + "|"
            markdown_output += "\n"

            markdown_output += "|"
            for i in range(len(header)):
                markdown_output += "---|"
            markdown_output += "\n"

        if rows:
            for row in rows:
                markdown_output += "|"
                for cell in row:
                    markdown_output += cell + "|"
                markdown_output += "\n"

    markdown_output += "\n"
    return markdown_output


def handle_thead(data):
    header = []
    if "$$" in data:
        for item in data["$$"]:
            if item["#name"] == "row":
                row_data = []
                if "$$" in item:
                    for entry in item["$$"]:
                        if entry["#name"] == "entry":
                            if "_" in entry:
                                row_data.append(handle_label(entry))
                            else:
                                row_data.append("")
                header.append(row_data)
    # Flatten the header list
    return header[0] if header else []


def handle_tbody(data):
    rows = []
    if "$$" in data:
        for item in data["$$"]:
            if item["#name"] == "row":
                row_data = []
                col_index = 0
                if "$$" in item:
                    for entry in item["$$"]:
                        if entry["#name"] == "entry":
                            content = ""

                            if "$" in entry:  # Check if "$" exists
                                if "align" in entry["$"]:
                                    if entry["$"]["align"] == "left":
                                        content = ""  # Reset content for left alignment
                                if "namest" in entry["$"] and "nameend" in entry["$"]:
                                    start_col = int(entry["$"]["namest"][-1]) - 1
                                    end_col = int(entry["$"]["nameend"][-1]) - 1
                                    spanned_cols = end_col - start_col + 1

                                    # Add empty cells for any skipped columns
                                    while col_index < start_col:
                                        row_data.append("")
                                        col_index += 1

                                    content = handle_label(entry)

                                    row_data.append(content)
                                    col_index += 1

                                    # Fill in empty cells for spanned columns
                                    for _ in range(spanned_cols - 1):
                                        row_data.append("")
                                        col_index += 1
                                else:
                                    # Add empty cells for any skipped columns
                                    while col_index < (
                                        int(entry["$"]["colname"][-1]) - 1
                                        if "colname" in entry["$"]
                                        else col_index
                                    ):
                                        row_data.append("")
                                        col_index += 1

                                    content = handle_label(entry)
                                    row_data.append(content)
                                    col_index += 1
                                        else:
                                content = handle_label(entry)
                                row_data.append(content)
                                col_index += 1

                rows.append(row_data)
    return rows


def handle_outline(data):
    markdown_output = ""
    if "$$" in data:
        for item in data["$$"]:
            if item.get("#name") == "list":
                markdown_output += handle_list(item)
    return markdown_output


def handle_section(data):
    return f"\n\n---\n\n{handle_label(data)}\n\n---\n\n"


def handle_section_title(data):
    return "## " + handle_label(data) + "\n\n"


def handle_br(data):
    return "<br>"


def handle_bold(data):
    return f"**{handle_label(data)}**"


def handle_italic(data):
    return f"*{handle_label(data)}*"


def handle_small_caps(data):
    # Small caps are not supported in Markdown, so we convert them to uppercase
    upper = handle_label(data).upper()
    # then make it small using latex format
    return "$_{" + upper + "}$"


def handle_sup(data):
    return "$^{" + handle_label(data) + "}$"


def handle_inf(data):
    text = handle_label(data)
    # we need to add many / when special characters can come
    if "$" in data:
        loc = data["$"]["loc"]
        if loc == "pre":
            return "$^{" + text + "}$"
        elif loc == "post":
            return "$_{" + text + "}$"
        else:
            print(f"Unhandled loc: {loc}")
            print(data)
    return "$_{" + text + "}$"


def handle_hsp(data):
    return " "


# formula
def handle_formula(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    if "$" in data:
        if "id" in data["$"]:
            id = data["$"]["id"]
            markdown_output += f" [^({id})]"
    return markdown_output


def handle_glyph(data):
    if "$" in data:
        if "name" in data["$"]:
            name = data["$"]["name"]
            if name in glyph_match:
                filename = glyph_match[name]["fileName"]
                description = (
                    glyph_match[name]["description"]
                    if "description" in glyph_match[name]
                    else ""
                )
                unicode = (
                    glyph_match[name]["unicode"]
                    if "unicode" in glyph_match[name]
                    else None
                )

                if unicode:
                    return f"&#x{unicode:x};"

                base_path = "https://sdfestaticassets-us-east-1.sciencedirectassets.com/shared-assets/55/entities/"
                return f"![{description}]({base_path}{filename})"


def handle_label(data):
    _data = ""
    subdata = ""
    if "_" in data:
        _data = data["_"]
    if "$$" in data:
        for item in data["$$"]:
            subdata += json_to_markdown(item)
    return _data + subdata


def handle_cross_ref(data):
    if "refid" in data["$"]:
        refid = data["$"]["refid"]
        link_text = handle_label(data)
        return f"[{link_text}](#{refid})"
    return handle_label(data) if "_" in data else ""


def handle_inter_ref(data):
    if "href" in data["$"]:
        href = data["$"]["href"]
        return f"[{handle_label(data) if '_' in data else ''}]({href})"
    return handle_label(data) if "_" in data else ""


def handle_intra_ref(data):
    if "href" in data["$"]:
        href = data["$"]["href"]
        # Modify the href as per the rule:
        # Replace ':' with '/', and remove '-' and '.'
        modified_href = "https://www.sciencedirect.com/science/article/" + href.replace(
            ":", "/"
        ).replace("-", "").replace(".", "")
        return f"[{handle_label(data) if '_' in data else ''}]({modified_href})"
    return handle_label(data) if "_" in data else ""


def handle_display(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    return markdown_output


def handle_textbox(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    return markdown_output


def handle_caption(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    return markdown_output


def handle_textbox_body(data):
    markdown_output = ""
    if "$$" in data:
        markdown_output += json_to_markdown(data["$$"])
    return markdown_output


def handle_inline_figure(data):
    global attachment_lookup
    if "$$" in data:
        if data["$$"][0]["#name"] == "link":
            link = data["$$"][0]
            if "$" in link and "locator" in link["$"]:
                locator = link["$"]["locator"]

                # Look up the attachment-eid using the locator
                attachment_eid = attachment_lookup.get(locator)

                if attachment_eid:
                    image_url = construct_image_url(attachment_eid)
                    return f"![]({image_url})"
    return ""


def handle_link(data):
    if "locator" in data["$"]:
        image_url = construct_image_url(data["$"]["locator"])
        return f"![]({image_url})"
    return ""


def construct_image_url(locator):
    """
    Constructs an image URL from the given locator.

    Args:
        locator: The locator string.

    Returns:
        The constructed image URL.
    """
    return f"https://ars.els-cdn.com/content/image/{locator}"


def handle_post_process(markdown_output):
    """
    Post-processes the Markdown output to fix formatting issues.

    Args:
        markdown_output: The Markdown output to post-process.

    Returns:
        The post-processed Markdown output.
    """
    # Remove extra newlines
    markdown_output = re.sub(r"\n{3,}", "\n\n", markdown_output)

    # Remove extra spaces before newlines
    markdown_output = re.sub(r" +\n", "\n", markdown_output)

    # remove extra ---
    markdown_output = re.sub(r"\n---\n\n---\n", "\n---\n", markdown_output)

    return markdown_output


def remove_trailing_commas(json_string):
    """Removes trailing commas from a JSON string."""

    # Remove trailing commas in objects and arrays
    cleaned_json_string = re.sub(r",\s*}", "}", json_string)
    cleaned_json_string = re.sub(r",\s*]", "]", cleaned_json_string)

    return cleaned_json_string


# Entry point for Streamlit app
def main():
    st.set_page_config(layout="wide")
    colx, coly = st.columns([3, 2], vertical_alignment="bottom")
    with colx:
        st.title("Sciencedirect JSON to Markdown")
        st.markdown(
            """
            This tool eats data from Sciencedirect. You may manually copy the json from the devtools:\n1. Open the paper/charpter you want to read, then press F12; \n2. Go to the network tab, search `body`; \n3. Press `Ctrl+R`, refresh the page;\n4. click the first item in the search result, go to the response tab, select all and copy;\n 5. Paste the json below, or save the json as file, then upload it to the upload box on the right.
            """
        )
    with coly:
        # upload JSON file
        uploaded_file = st.file_uploader(
            "Upload JSON file",
            type=["json"],
            label_visibility="collapsed",
            help="Upload a JSON file to convert to Markdown.",
        )
        
        colm, coln = st.columns(2)
        with colm:
            convert = st.button("Convert")
        with coln:
            hide_original = st.checkbox("Hide Raw Markdown", value=True)
    
    # Input JSON data
    json_data = st.text_area(
        "Upload JSON data at the top, or paste it here.",
        placeholder="Paste JSON data here...",
    )

    cola, colb = st.columns(2)

    if not convert:
        st.stop()

    try:
        if uploaded_file:
            json_data = uploaded_file.read().decode("utf-8")
        cleaned_json_data = remove_trailing_commas(json_data)
        data = json.loads(cleaned_json_data)
        markdown_output = json_to_markdown(data)
    except json.JSONDecodeError:
        st.error("Invalid JSON format. Please check your input.")
    except Exception as e:
        st.error(f"An error occurred: {e.__cause__}")
        st.exception(e)

    with cola:
        st.header("Markdown Output")
    with colb:
        with colm:
            title_input = st.text_input(
                "Title",
                "converted_markdown.md",
                label_visibility="collapsed",
            )
        with coln:
            # Download button
            st.download_button(
                label="Download Markdown",
                data=markdown_output.encode("utf-8"),
                file_name=title_input,
                mime="text/markdown",
            )

    if hide_original:
        st.markdown(markdown_output, unsafe_allow_html=True)
    else:
        with cola:
            st.markdown(markdown_output, unsafe_allow_html=True)
        with colb:
            st.header("Markdown Output Raw")
            st.markdown(f"```markdown\n{markdown_output}\n```")


if __name__ == "__main__":
    main()
