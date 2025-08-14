#
# Bitcoin Safe
# Copyright (C) 2024 Andreas Griffin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see https://www.gnu.org/licenses/gpl-3.0.html
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import logging
from functools import _lru_cache_wrapper, lru_cache
from typing import List

logger = logging.getLogger(__name__)

cached_always_keep_functions = []
cached_functions: List[_lru_cache_wrapper] = []


def clear_cache():
    for f in cached_functions:
        f.cache_clear()


def register_cache(always_keep=False):
    def wrapper(func):
        # Decorate the function with lru_cache
        cached_func = lru_cache(maxsize=None)(func)

        # Logging
        logger.debug(f"register_cache always_keep {always_keep}")

        # Store the decorated function
        if always_keep:
            cached_always_keep_functions.append(cached_func)
        else:
            cached_functions.append(cached_func)

        return cached_func

    return wrapper
