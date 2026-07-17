import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.gmail_client import extract_doc_url, extract_meeting_name


def test_extract_doc_url_from_html():
    html = '<p>Notes</p><a href="https://docs.google.com/document/d/1abc123def/edit">View</a>'
    result = extract_doc_url(html)
    assert result == "https://docs.google.com/document/d/1abc123def/edit"


def test_extract_doc_url_no_link():
    html = "<p>No link here</p>"
    result = extract_doc_url(html)
    assert result is None


def test_extract_doc_url_multiple_links():
    html = '<a href="https://meet.google.com/abc">Meet</a><a href="https://docs.google.com/document/d/xyz789/edit">Notes</a>'
    result = extract_doc_url(html)
    assert result == "https://docs.google.com/document/d/xyz789/edit"


def test_extract_meeting_name_standard():
    subject = 'Notes: "Grace / Ignas 1:1" Jul 17, 2026'
    result = extract_meeting_name(subject)
    assert result == "Grace / Ignas 1:1"


def test_extract_meeting_name_no_quotes():
    subject = "Notes: Some Meeting Jul 17, 2026"
    result = extract_meeting_name(subject)
    assert result == "Some Meeting Jul 17, 2026"


def test_extract_meeting_name_complex():
    subject = 'Notes: "AI First Dev: Epic Creator" Jul 15, 2026'
    result = extract_meeting_name(subject)
    assert result == "AI First Dev: Epic Creator"


if __name__ == "__main__":
    test_extract_doc_url_from_html()
    print("✓ extract_doc_url from HTML")
    test_extract_doc_url_no_link()
    print("✓ extract_doc_url no link")
    test_extract_doc_url_multiple_links()
    print("✓ extract_doc_url multiple links")
    test_extract_meeting_name_standard()
    print("✓ extract_meeting_name standard")
    test_extract_meeting_name_no_quotes()
    print("✓ extract_meeting_name no quotes")
    test_extract_meeting_name_complex()
    print("✓ extract_meeting_name complex")
    print("\nAll gmail_client tests passed.")
