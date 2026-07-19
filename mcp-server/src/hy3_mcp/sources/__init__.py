# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""External data sources for hy3-mcp.

Exactly two, per the issue's "1~2 extra data sources" requirement:

* :mod:`hy3_mcp.sources.files` — sandboxed local file reading + deterministic
  keyword retrieval (data source #1).
* :mod:`hy3_mcp.sources.search` — pluggable web search: offline stub by
  default, Tavily behind an env-provided key (data source #2).
"""
