import re
from html import escape

from bs4 import BeautifulSoup
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin

from .common import logger
from .export import Export


class MetaDescription(BasePlugin):

    config_scheme = (
        ("export_csv", config_options.Type(bool, default=False)),
        ("verbose", config_options.Type(bool, default=False)),
    )

    def __init__(self):
        self._headings_pattern = re.compile("<h[2-6]", flags=re.IGNORECASE)
        self._pages = []
        self._count_meta = 0             # Pages with meta descriptions defined on the page meta-data
        self._count_first_paragraph = 0  # Pages with meta descriptions from the first paragraph
        self._count_empty = 0            # Pages without meta descriptions

    def _get_first_paragraph_text(self, html):
        # Strip page subsections to improve performance
        html = re.split(self._headings_pattern, html, maxsplit=1)[0]
        # Select first paragraph directly under body
        first_paragraph = BeautifulSoup(html, "html.parser").select_one("p:not(div.admonition > p)")
        if first_paragraph is not None:
            # Found the first paragraph, return stripped and escaped text
            return escape(first_paragraph.get_text().strip())
        else:
            # Didn't find the first paragraph
            return ""

    def on_config(self, config):
        logger.initialize(self.config)
        return config

    def on_page_content(self, html, page, config, files):
        if page.meta.get("description", None):
            # Skip pages that already have an explicit meta description
            self._count_meta += 1
        else:
            # Create meta description based on the first paragraph of the page
            first_paragraph_text = self._get_first_paragraph_text(html)
            if len(first_paragraph_text) > 0:
                page.meta["description"] = first_paragraph_text
                self._count_first_paragraph += 1
            else:
                self._count_empty += 1
        return html

    def on_post_page(self, output, page, config):
        if self.config.get("export_csv", False):
            # Collect pages to export meta descriptions to CSV file
            self._pages.append(page)
        return output

    def on_post_build(self, config):
        summary = \
            f"{self._count_meta + self._count_first_paragraph} out of " \
            f"{self._count_meta + self._count_first_paragraph + self._count_empty} pages have meta descriptions " \
            f"({self._count_first_paragraph} use the first paragraph)"
        logger.write(logger.Info, summary)
        if self.config.get("export_csv", False):
            # Export meta descriptions to CSV file
            Export(self._pages, config).write_csv()
