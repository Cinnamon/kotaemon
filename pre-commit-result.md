check yaml...............................................................[42mPassed[m
check toml...............................................................[42mPassed[m
fix end of files.........................................................[42mPassed[m
trim trailing whitespace.................................................[42mPassed[m
mixed line ending........................................................[42mPassed[m
detect aws credentials...................................................[42mPassed[m
detect private key.......................................................[42mPassed[m
check for added large files..............................................[42mPassed[m
debug statements (python)................................................[42mPassed[m
ruff check...............................................................[42mPassed[m
ruff format..............................................................[42mPassed[m
mypy.....................................................................[41mFailed[m
[2m- hook id: mypy[m
[2m- exit code: 1[m

libs/kotaemon/kotaemon/contribs/promptui/base.py:23: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/blocks.py:20: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/blocks.py:31: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/blocks.py:38: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/blocks.py:72: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/blocks.py:77: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"AsyncGenerator"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/base/schema.py:43: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/schema.py:93: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/schema.py:99: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/schema.py:132: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/table.py:82: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/table.py:82: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/table.py:258: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/table.py:258: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:10: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:34: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:52: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:75: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:90: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_missing_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:92: [1m[31merror:(B[m Call to untyped function (B[m[1m"partial_populate"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:94: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:105: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_redundant_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/template.py:130: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:6: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:6: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_documents.py:14: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:14: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_documents.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:23: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_documents.py:35: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:35: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_documents.py:43: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_documents.py:43: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/base/component.py:46: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/component.py:48: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/component.py:50: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/component.py:52: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/base/component.py:55: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:60: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:60: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:61: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:115: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:115: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:116: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:186: [1m[31merror:(B[m Argument 1 to (B[m[1m"box_h"(B[m has incompatible type (B[m[1m"tuple[int, int, int, int]"(B[m; expected (B[m[1m"list[int]"(B[m  (B[m[33m[arg-type](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:187: [1m[31merror:(B[m Argument 1 to (B[m[1m"box_w"(B[m has incompatible type (B[m[1m"tuple[int, int, int, int]"(B[m; expected (B[m[1m"list[int]"(B[m  (B[m[33m[arg-type](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:227: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:228: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/pdf_ocr.py:229: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
flowsettings.py:333: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/docs.py:7: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/docs.py:40: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/__init__.py:8: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/base.py:18: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/base.py:31: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/base.py:38: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/base.py:39: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:16: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:28: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:29: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:30: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:60: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/base.py:76: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/base.py:100: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:105: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/base.py:150: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/base.py:158: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/base.py:158: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:16: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:22: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:39: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:39: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:49: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:69: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:69: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:79: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:79: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:87: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_li_class"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:112: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:115: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:136: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:136: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/base.py:140: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:11: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:14: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:14: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:45: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:51: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/base.py:56: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/parsers/regex_extractor.py:27: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/parsers/regex_extractor.py:48: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/unstructured_loader.py:52: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/unstructured_loader.py:55: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/pdf_loader.py:71: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:24: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:36: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:37: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:86: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:115: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:116: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:123: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:134: [1m[31merror:(B[m Item (B[m[1m"str"(B[m of (B[m[1m"Message[str, str] | str | Any"(B[m has no attribute (B[m[1m"get_content_type"(B[m  (B[m[33m[union-attr](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:135: [1m[31merror:(B[m Item (B[m[1m"str"(B[m of (B[m[1m"Message[str, str] | str | Any"(B[m has no attribute (B[m[1m"get_payload"(B[m  (B[m[33m[union-attr](B[m
libs/kotaemon/kotaemon/loaders/html_loader.py:135: [1m[31merror:(B[m Item (B[m[1m"Message[str, str]"(B[m of (B[m[1m"Message[str, str] | bytes | Any"(B[m has no attribute (B[m[1m"decode"(B[m  (B[m[33m[union-attr](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:33: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:44: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:48: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:49: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:126: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:137: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:141: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/excel_loader.py:142: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/docx_loader.py:21: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docx_loader.py:30: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docx_loader.py:45: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docx_loader.py:46: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/base.py:63: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/base.py:77: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/base.py:84: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:27: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:34: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:36: [1m[31merror:(B[m Call to untyped function (B[m[1m"__set"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:38: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:53: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:53: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:69: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:96: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:108: [1m[31merror:(B[m Call to untyped function (B[m[1m"__check_redundant_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:109: [1m[31merror:(B[m Call to untyped function (B[m[1m"__validate_value_type"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:113: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:122: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:141: [1m[31merror:(B[m Call to untyped function (B[m[1m"__prepare"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:143: [1m[31merror:(B[m Call to untyped function (B[m[1m"__prepare"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:152: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:166: [1m[31merror:(B[m Call to untyped function (B[m[1m"__set"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:168: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:179: [1m[31merror:(B[m Call to untyped function (B[m[1m"__set"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:180: [1m[31merror:(B[m Call to untyped function (B[m[1m"__check_unset_placeholders"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:181: [1m[31merror:(B[m Call to untyped function (B[m[1m"__prepare_value"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/prompts/base.py:186: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/base.py:12: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/base.py:15: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/base.py:18: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/base.py:21: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/base.py:24: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/tavily_web_search.py:13: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/tavily_web_search.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/tavily_web_search.py:56: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:21: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:54: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:62: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:84: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:93: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:101: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/indices/base.py:108: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:112: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/base.py:121: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/base.py:7: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/base.py:12: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/base.py:17: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:15: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:34: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:63: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:63: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/chatbot/base.py:70: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:70: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/chatbot/base.py:86: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:86: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/chatbot/base.py:88: [1m[31merror:(B[m Call to untyped function (B[m[1m"start_session"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/chatbot/base.py:105: [1m[31merror:(B[m Call to untyped function (B[m[1m"end_session"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/chatbot/base.py:108: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/chatbot/base.py:112: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/utils.py:4: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/render.py:11: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/render.py:42: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/render.py:170: [1m[31merror:(B[m Call to untyped function (B[m[1m"is_close"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_telemetry.py:10: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_telemetry.py:10: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_telemetry.py:32: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_telemetry.py:32: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_telemetry.py:49: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_telemetry.py:49: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/utils/file.py:8: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/file.py:23: [1m[31merror:(B[m Call to untyped function (B[m[1m"remove_implicit_resolver"(B[m of (B[m[1m"YAMLNoDateSafeLoader"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:18: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:81: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:81: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:81: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:95: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:100: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:101: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:113: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/export.py:124: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:47: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:50: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:57: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:57: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:62: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:62: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/simple_file.py:66: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:9: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:22: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:27: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:49: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:49: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:66: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:66: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/qdrant.py:75: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:39: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:49: [1m[31merror:(B[m Argument 1 to (B[m[1m"isdir"(B[m has incompatible type (B[m[1m"Any | None"(B[m; expected (B[m[1m"int | str | bytes | PathLike[str] | PathLike[bytes]"(B[m  (B[m[33m[arg-type](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:50: [1m[31merror:(B[m Argument 1 to (B[m[1m"join"(B[m has incompatible type (B[m[1m"Any | None"(B[m; expected (B[m[1m"str"(B[m  (B[m[33m[arg-type](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:67: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:70: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:82: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:93: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:93: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:97: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:97: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/milvus.py:109: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:14: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:49: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:67: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:67: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:76: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:76: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/lancedb.py:83: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:32: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:32: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:46: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:55: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:55: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/in_memory.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:19: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:60: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:60: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:69: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:69: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/vectorstores/chroma.py:76: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:24: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:26: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:26: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:63: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:129: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:146: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:146: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/docstores/lancedb.py:156: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:13: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:16: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:67: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:73: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:85: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:90: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:93: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/in_memory.py:93: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:13: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:63: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:63: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:103: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:125: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:137: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:162: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:171: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:171: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/docstores/elasticsearch.py:176: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/rerankings/voyageai.py:14: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/rerankings/voyageai.py:38: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/rerankings/voyageai.py:43: [1m[31merror:(B[m Call to untyped function (B[m[1m"_import_voyageai"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/rerankings/voyageai.py:44: [1m[31merror:(B[m Call to untyped function (B[m[1m"_import_voyageai"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/loaders/txt_loader.py:10: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/txt_loader.py:11: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/txt_loader.py:15: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/txt_loader.py:16: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/composite_loader.py:38: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"List"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/composite_loader.py:39: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"List"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/composite_loader.py:48: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/base.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/splitters/__init__.py:11: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/splitters/__init__.py:25: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/splitters/__init__.py:32: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/splitters/__init__.py:46: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/extractors/doc_parsers.py:8: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/extractors/doc_parsers.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/extractors/doc_parsers.py:23: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/extractors/doc_parsers.py:31: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:19: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:19: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:45: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:50: [1m[31merror:(B[m Call to untyped function (B[m[1m"_import_voyageai"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:51: [1m[31merror:(B[m Call to untyped function (B[m[1m"_import_voyageai"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:53: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/voyageai.py:60: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:17: [1m[31merror:(B[m Module (B[m[1m"kotaemon.embeddings.base"(B[m does not explicitly export attribute (B[m[1m"Document"(B[m  (B[m[33m[attr-defined](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:17: [1m[31merror:(B[m Module (B[m[1m"kotaemon.embeddings.base"(B[m does not explicitly export attribute (B[m[1m"DocumentWithEmbedding"(B[m  (B[m[33m[attr-defined](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:68: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:75: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:83: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:87: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:104: [1m[31merror:(B[m Call to untyped function (B[m[1m"openai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:127: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:132: [1m[31merror:(B[m Call to untyped function (B[m[1m"openai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:156: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:185: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:187: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:213: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:217: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:248: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/openai.py:250: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:9: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:9: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:15: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_lc_class"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:17: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:21: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:32: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:40: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:50: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:60: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:65: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:74: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:92: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:112: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:124: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:142: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:168: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:184: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:205: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:215: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:238: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:250: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:273: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/langchain_based.py:285: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/fastembed.py:51: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/fastembed.py:68: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:41: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:56: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:57: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:66: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:67: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:76: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:77: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:129: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:146: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:146: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:146: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:166: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:195: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:205: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:209: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:209: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/pipeline.py:231: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:13: [1m[31merror:(B[m Call to untyped function (B[m[1m"__init__"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:34: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:34: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:52: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:57: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:57: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:59: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/storages/docstores/simple_file.py:62: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_post_processing.py:8: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_post_processing.py:14: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_post_processing.py:21: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_post_processing.py:27: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:12: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:18: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_lc_class"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:20: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:48: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:51: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:59: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:69: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:79: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:84: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:93: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:111: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:143: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:155: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:191: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:203: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/completions/langchain_based.py:221: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/llamacpp.py:82: [1m[31merror:(B[m Redundant cast to (B[m[1m"str"(B[m  (B[m[33m[redundant-cast](B[m
libs/kotaemon/kotaemon/llms/chats/llamacpp.py:104: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/llamacpp.py:121: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/llamacpp.py:142: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:16: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:21: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:24: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:25: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_lc_class"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:27: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:32: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:39: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:51: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:74: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:95: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_tool_call_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:108: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:112: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:117: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:119: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:125: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:131: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:134: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:142: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:152: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:162: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:167: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:176: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:191: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:192: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:210: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:219: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:220: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:240: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:249: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:260: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:263: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:277: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:286: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:298: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:307: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:321: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:330: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:339: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:353: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:362: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:376: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/langchain_based.py:390: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_splitter.py:42: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_splitter.py:42: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/settings.py:19: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:20: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:29: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:32: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/settings.py:32: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/settings.py:35: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/settings.py:64: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:72: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/settings.py:72: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/settings.py:88: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:114: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/settings.py:128: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:106: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:133: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:163: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:195: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:203: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:207: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:211: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:216: [1m[31merror:(B[m Call to untyped function (B[m[1m"openai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:221: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:227: [1m[31merror:(B[m Call to untyped function (B[m[1m"aopenai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:234: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:239: [1m[31merror:(B[m Call to untyped function (B[m[1m"openai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:262: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:267: [1m[31merror:(B[m Call to untyped function (B[m[1m"openai_response"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:285: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:307: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:331: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:333: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:336: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:337: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:348: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:382: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:410: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:412: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:416: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:418: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:440: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:444: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:468: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:492: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:494: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:497: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/openai.py:498: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_params"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/tools/base.py:38: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/tools/base.py:61: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/tools/base.py:61: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Tuple"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/tools/base.py:96: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/tools/base.py:132: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Callable"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/io/base.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:99: [1m[31merror:(B[m Need type annotation for (B[m[1m"log"(B[m (hint: (B[m[1m"log: list[<type>] = ..."(B[m)  (B[m[33m[var-annotated](B[m
libs/kotaemon/kotaemon/agents/io/base.py:101: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:101: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/agents/io/base.py:106: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:106: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:110: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:113: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:117: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:120: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:125: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:128: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:133: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:137: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:140: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:153: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:158: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:158: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/agents/io/base.py:163: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:163: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:168: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:171: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:178: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:178: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:182: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:185: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:185: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:189: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:192: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:192: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:196: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:199: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:199: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:203: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:206: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:206: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/io/base.py:210: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_log"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/io/base.py:225: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/io/base.py:237: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/io/base.py:258: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/utils/hf_papers.py:18: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:38: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:48: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:57: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:72: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:73: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_paper_id_from_name"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/utils/hf_papers.py:79: [1m[31merror:(B[m Call to untyped function (B[m[1m"filter_recommendations"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/utils/hf_papers.py:81: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_recommendation_into_markdown"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/utils/hf_papers.py:85: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/hf_papers.py:98: [1m[31merror:(B[m Call to untyped function (B[m[1m"parse_date"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/help.py:35: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/utils.py:14: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/utils.py:20: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/utils.py:25: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/utils.py:26: [1m[31merror:(B[m Call to untyped function (B[m[1m"is_arxiv_url"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/utils.py:44: [1m[31merror:(B[m Call to untyped function (B[m[1m"clean_name"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/rerankings/tei_fast_rerank.py:40: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/rerankings/tei_fast_rerank.py:79: [1m[31merror:(B[m Call to untyped function (B[m[1m"client"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/loaders/web_loader.py:16: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/web_loader.py:17: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/web_loader.py:21: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/web_loader.py:36: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/web_loader.py:37: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:26: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:54: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:62: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:63: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:157: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/ocr_loader.py:158: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/mathpix_loader.py:57: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/mathpix_loader.py:64: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/mathpix_loader.py:205: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/mathpix_loader.py:274: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/chats/endpoint_based.py:28: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/endpoint_based.py:47: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/endpoint_based.py:79: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/chats/endpoint_based.py:85: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/jina_web_search.py:15: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/jina_web_search.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/retrievers/jina_web_search.py:56: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/tei_endpoint_embed.py:35: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/tei_endpoint_embed.py:48: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/embeddings/tei_endpoint_embed.py:74: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:32: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:40: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:40: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:73: [1m[31merror:(B[m Call to untyped function (B[m[1m"download_binary"(B[m of (B[m[1m"Tunnel"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:77: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/tunnel.py:77: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/loaders/utils/adobe.py:148: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/adobe.py:225: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"List"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/utils/adobe.py:226: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"List"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/components.py:42: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/components.py:65: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/components.py:69: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/components.py:83: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/components.py:91: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/components.py:185: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/tests/test_vectorstore.py:17: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:30: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:44: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:58: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:74: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:88: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_vectorstore.py:97: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:97: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_vectorstore.py:108: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:135: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:163: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:179: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:196: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:213: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:238: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:250: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_vectorstore.py:257: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:257: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_vectorstore.py:273: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:289: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:314: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:336: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_vectorstore.py:358: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_docstores.py:215: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_docstores.py:218: [1m[31merror:(B[m Call to untyped function (B[m[1m"InMemoryDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_docstores.py:264: [1m[31merror:(B[m Call to untyped function (B[m[1m"InMemoryDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_docstores.py:271: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_docstores.py:329: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:111: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:122: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:123: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:127: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:128: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py:144: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/adobe_loader.py:56: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/adobe_loader.py:57: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/linear.py:52: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/linear.py:52: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/linear.py:55: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/linear.py:56: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/linear.py:74: [1m[31merror:(B[m Argument after ** must be a mapping, not (B[m[1m"dict[Any, Any] | None"(B[m  (B[m[33m[arg-type](B[m
libs/kotaemon/kotaemon/llms/linear.py:120: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/linear.py:124: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/linear.py:125: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/cot.py:86: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/cot.py:88: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/llms/cot.py:90: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/cot.py:151: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Callable"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/cot.py:156: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/visualize_cited.py:34: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/visualize_cited.py:38: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/visualize_cited.py:44: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/visualize_cited.py:114: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/utils/visualize_cited.py:121: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_projections"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/utils/visualize_cited.py:134: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_projections"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:31: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:42: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:50: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:58: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:66: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:74: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:82: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:90: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:96: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:104: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:110: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:123: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:133: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:143: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:151: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:156: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:156: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_embedding_models.py:159: [1m[31merror:(B[m Call to untyped function (B[m[1m"assert_embedding_result"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_embedding_models.py:169: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_embedding_models.py:170: [1m[31merror:(B[m Call to untyped function (B[m[1m"VoyageAIEmbeddings"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:45: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:53: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:54: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:58: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:59: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/loaders/docling_loader.py:223: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/llms/branching.py:54: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/branching.py:63: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/branching.py:128: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/branching.py:128: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/branching.py:163: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/llms/branching.py:181: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem_tests/test_qa.py:41: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem_tests/test_qa.py:49: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_template.py:68: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_missing_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_template.py:82: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_redundant_kwargs"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_template.py:85: [1m[31merror:(B[m Call to untyped function (B[m[1m"partial_populate"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_template.py:111: [1m[31merror:(B[m Call to untyped function (B[m[1m"partial_populate"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:8: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:8: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:16: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:23: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:25: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:30: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:30: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:32: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:37: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:37: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:39: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:44: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:44: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:52: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_prompt.py:59: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_prompt.py:61: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_prompt.py:62: [1m[31merror:(B[m Call to untyped function (B[m[1m"set_value"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_llms_completion_models.py:43: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_llms_completion_models.py:52: [1m[31merror:(B[m Call to untyped function (B[m[1m"to_langchain_format"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_llms_completion_models.py:66: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_llms_completion_models.py:75: [1m[31merror:(B[m Call to untyped function (B[m[1m"to_langchain_format"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_llms_completion_models.py:86: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_llms_completion_models.py:86: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_llms_completion_models.py:91: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_lc_class"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_llms_chat_models.py:47: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_llms_chat_models.py:77: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_llms_chat_models.py:77: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_cot.py:40: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_cot.py:71: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_cot.py:100: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:42: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:52: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:57: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:58: [1m[31merror:(B[m Call to untyped function (B[m[1m"BasePromptComponent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_composite.py:62: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:69: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:79: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:88: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:100: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:116: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:132: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_composite.py:146: [1m[31merror:(B[m Call to untyped function (B[m[1m"run"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_composite.py:154: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation.py:28: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation.py:31: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation.py:67: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation.py:97: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:15: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:25: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:32: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:39: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:46: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_table_reader.py:46: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:20: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reader.py:20: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:21: [1m[31merror:(B[m Call to untyped function (B[m[1m"DocxReader"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_reader.py:27: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reader.py:27: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:36: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reader.py:36: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:58: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reader.py:58: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:77: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reader.py:77: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_reader.py:87: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/_test_multimodal_reader.py:14: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/_test_multimodal_reader.py:14: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/ingests/files.py:90: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/ingests/files.py:107: [1m[31merror:(B[m Call to untyped function (B[m[1m"DirectoryReader"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/indices/rankings/llm_trulens.py:46: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Pattern"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/indices/rankings/llm_trulens.py:52: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/rankings/llm_trulens.py:145: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/solver.py:24: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:46: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:67: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:68: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:77: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:78: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:87: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:88: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:155: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:172: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:191: [1m[31merror:(B[m Call to untyped function (B[m[1m"ChatConversation"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:193: [1m[31merror:(B[m Call to untyped function (B[m[1m"start_session"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:209: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:242: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:242: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/chat.py:287: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:15: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:33: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:64: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:86: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:89: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:117: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/config.py:130: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/agents/base.py:37: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/base.py:38: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/base.py:55: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_ingestor.py:7: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_ingestor.py:7: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/__init__.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/__init__.py:12: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/__init__.py:17: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/contribs/promptui/ui/__init__.py:29: [1m[31merror:(B[m Call to untyped function (B[m[1m"build_chat_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/rewoo/planner.py:3: [1m[31merror:(B[m Module (B[m[1m"kotaemon.agents.base"(B[m does not explicitly export attribute (B[m[1m"BaseLLM"(B[m  (B[m[33m[attr-defined](B[m
libs/kotaemon/kotaemon/agents/rewoo/planner.py:3: [1m[31merror:(B[m Module (B[m[1m"kotaemon.agents.base"(B[m does not explicitly export attribute (B[m[1m"BaseTool"(B[m  (B[m[33m[attr-defined](B[m
libs/kotaemon/kotaemon/agents/rewoo/planner.py:41: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/planner.py:85: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:8: [1m[31merror:(B[m Module (B[m[1m"kotaemon.agents.base"(B[m does not explicitly export attribute (B[m[1m"BaseLLM"(B[m  (B[m[33m[attr-defined](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:116: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:175: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:175: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/agents/react/agent.py:181: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:197: [1m[31merror:(B[m Call to untyped function (B[m[1m"clear"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:250: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/react/agent.py:266: [1m[31merror:(B[m Call to untyped function (B[m[1m"clear"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/langchain_based.py:28: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/langchain_based.py:35: [1m[31merror:(B[m Call to untyped function (B[m[1m"update_agent_tools"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/langchain_based.py:37: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/langchain_based.py:37: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/agents/langchain_based.py:64: [1m[31merror:(B[m Call to untyped function (B[m[1m"update_agent_tools"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/db/base_models.py:37: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/db/base_models.py:82: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/db/base_models.py:99: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/db/base_models.py:100: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/db/base_models.py:101: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/cli.py:113: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/cli.py:121: [1m[31merror:(B[m Incompatible types in assignment (expression has type (B[m[1m"int"(B[m, variable has type (B[m[1m"str"(B[m)  (B[m[33m[assignment](B[m
libs/kotaemon/kotaemon/cli.py:132: [1m[31merror:(B[m Call to untyped function (B[m[1m"Tunnel"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:49: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:58: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:153: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:153: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:194: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:240: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:245: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/agents/rewoo/agent.py:312: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/models.py:11: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/models.py:16: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:10: [1m[31merror:(B[m Module (B[m[1m"ktem.rerankings.db"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/rerankings/manager.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:16: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/rerankings/manager.py:18: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:20: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Type"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:34: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/manager.py:35: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_vendors"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/manager.py:37: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:37: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/rerankings/manager.py:54: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:54: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/rerankings/manager.py:77: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:85: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:134: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:138: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:138: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:155: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/manager.py:157: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:167: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/manager.py:169: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/manager.py:169: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:190: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/manager.py:192: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/manager.py:197: [1m[31merror:(B[m Call to untyped function (B[m[1m"RerankingManager"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:10: [1m[31merror:(B[m Module (B[m[1m"ktem.llms.db"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/llms/manager.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:16: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/llms/manager.py:18: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:20: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Type"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:36: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:37: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_vendors"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:39: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:39: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/llms/manager.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:56: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/llms/manager.py:98: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:106: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:155: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:159: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:159: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:178: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:180: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:190: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:192: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/manager.py:192: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:213: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/manager.py:215: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/manager.py:220: [1m[31merror:(B[m Call to untyped function (B[m[1m"LLMManager"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:10: [1m[31merror:(B[m Module (B[m[1m"ktem.embeddings.db"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/embeddings/manager.py:16: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:16: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/embeddings/manager.py:18: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:20: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Type"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:34: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:35: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_vendors"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:37: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:37: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/embeddings/manager.py:55: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:55: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/embeddings/manager.py:94: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:102: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:151: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:155: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:155: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:173: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:175: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:185: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:187: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/manager.py:187: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:208: [1m[31merror:(B[m Call to untyped function (B[m[1m"load"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/manager.py:210: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/manager.py:215: [1m[31merror:(B[m Call to untyped function (B[m[1m"EmbeddingManager"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:34: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:61: [1m[31merror:(B[m Call to untyped function (B[m[1m"generate_chat_completion_obj"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:66: [1m[31merror:(B[m Call to untyped function (B[m[1m"generate_chat_completion_obj"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:71: [1m[31merror:(B[m Call to untyped function (B[m[1m"generate_chat_completion_obj"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:93: [1m[31merror:(B[m Call to untyped function (B[m[1m"generate_chat_completion_obj"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:116: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:129: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:148: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:166: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:184: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:209: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_agent.py:215: [1m[31merror:(B[m Call to untyped function (B[m[1m"LangchainAgent"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_agent.py:229: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:93: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:93: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:188: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/rewoo.py:198: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:221: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:252: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:263: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/rewoo.py:275: [1m[31merror:(B[m Call to untyped function (B[m[1m"find_text"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/rewoo.py:338: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/rewoo.py:339: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/rewoo.py:355: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/rewoo.py:356: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/rewoo.py:375: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_info_panel_planner"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/rewoo.py:380: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_info_panel_evidence"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/rewoo.py:394: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/rewoo.py:394: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/rewoo.py:442: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/rewoo.py:500: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/react.py:56: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/react.py:169: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/react.py:190: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/react.py:214: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:215: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/react.py:231: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/react.py:231: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/react.py:231: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:240: [1m[31merror:(B[m Call to untyped function (B[m[1m"stream"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/react.py:265: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:265: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:302: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/react.py:342: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/prompt_optimization/suggest_conversation_name.py:25: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/prompt_optimization/rewrite_question.py:31: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/prompt_optimization/mindmap.py:80: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/prompt_optimization/fewshot_rewrite_question.py:40: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/prompt_optimization/fewshot_rewrite_question.py:40: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/prompt_optimization/fewshot_rewrite_question.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/prompt_optimization/fewshot_rewrite_question.py:59: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/prompt_optimization/fewshot_rewrite_question.py:79: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/prompt_optimization/decompose_question.py:45: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/prompt_optimization/decompose_question.py:66: [1m[31merror:(B[m Call to untyped function (B[m[1m"create_prompt"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:121: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:121: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:143: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:148: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:210: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:210: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:214: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:214: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:296: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:296: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:298: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa.py:322: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:91: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:91: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:103: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:152: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:161: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:215: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:215: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:322: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:322: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py:324: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/tests/test_reranking.py:43: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_reranking.py:56: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:36: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:45: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:79: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:84: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:95: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:100: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:127: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:134: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:193: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:193: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:208: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:208: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/kotaemon/indices/vectorindex.py:310: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:46: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:108: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:165: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:205: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:222: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:279: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:280: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/simple.py:281: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/simple.py:288: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:289: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/simple.py:304: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:304: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/reasoning/simple.py:336: [1m[31merror:(B[m Call to untyped function (B[m[1m"show_citations_and_addons"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/simple.py:341: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:348: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:348: [1m[31merror:(B[m Signature of (B[m[1m"get_pipeline"(B[m incompatible with supertype (B[m[1m"ktem.reasoning.base.BaseReasoning"(B[m  (B[m[33m[override](B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m      Superclass:(B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m          def get_pipeline(cls, user_settings: dict[Any, Any], state: dict[Any, Any], retrievers: list[BaseComponent] | None = ...) -> BaseReasoning(B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m      Subclass:(B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/reasoning/simple.py:348: [34mnote:(B[m          def get_pipeline(cls, settings: Any, states: Any, retrievers: Any) -> Any(B[m
libs/ktem/ktem/reasoning/simple.py:357: [1m[31merror:(B[m Call to untyped function (B[m[1m"prepare_pipeline_instance"(B[m of (B[m[1m"FullQAPipeline"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/reasoning/simple.py:405: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:482: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:495: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:495: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:496: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:532: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:533: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/reasoning/simple.py:590: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/reasoning/simple.py:599: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/reasoning/simple.py:610: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/kotaemon/tests/test_tools.py:40: [1m[31merror:(B[m Call to untyped function (B[m[1m"InMemoryDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:18: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/pipelines.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:109: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/pipelines.py:113: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:144: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/pipelines.py:194: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/pipelines.py:224: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/pipelines.py:281: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:281: [1m[31merror:(B[m Signature of (B[m[1m"get_pipeline"(B[m incompatible with supertype (B[m[1m"ktem.index.file.base.BaseFileIndexRetriever"(B[m  (B[m[33m[override](B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m      Superclass:(B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m          def get_pipeline(cls, user_settings: dict[Any, Any], index_settings: dict[Any, Any], selected: list[Any] | None = ...) -> BaseFileIndexRetriever(B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m      Subclass:(B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/index/file/pipelines.py:281: [34mnote:(B[m          def get_pipeline(cls, user_settings: Any, index_settings: Any, selected: Any) -> Any(B[m
libs/ktem/ktem/index/file/pipelines.py:310: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/pipelines.py:352: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:391: [1m[31merror:(B[m Call to untyped function (B[m[1m"handle_chunks_docstore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:398: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:404: [1m[31merror:(B[m Call to untyped function (B[m[1m"handle_chunks_vectorstore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:416: [1m[31merror:(B[m Call to untyped function (B[m[1m"insert_chunks_to_vectorstore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:419: [1m[31merror:(B[m Call to untyped function (B[m[1m"insert_chunks_to_vectorstore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:424: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:443: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:475: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"tuple"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/pipelines.py:504: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/pipelines.py:530: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/pipelines.py:555: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_token_func"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/pipelines.py:568: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:572: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:597: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:602: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:674: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:690: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:709: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:776: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/pipelines.py:781: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_indexing_retrieval.py:21: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_indexing_retrieval.py:23: [1m[31merror:(B[m Call to untyped function (B[m[1m"InMemoryDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/kotaemon/tests/test_indexing_retrieval.py:45: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_indexing_retrieval.py:47: [1m[31merror:(B[m Call to untyped function (B[m[1m"InMemoryDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:13: [1m[31merror:(B[m Module (B[m[1m"ktem.index.file.pipelines"(B[m does not explicitly export attribute (B[m[1m"BaseFileIndexRetriever"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:59: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:119: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [1m[31merror:(B[m Signature of (B[m[1m"get_pipeline"(B[m incompatible with supertype (B[m[1m"ktem.index.file.base.BaseFileIndexRetriever"(B[m  (B[m[33m[override](B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m      Superclass:(B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m          def get_pipeline(cls, user_settings: dict[Any, Any], index_settings: dict[Any, Any], selected: list[Any] | None = ...) -> BaseFileIndexRetriever(B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m      Subclass:(B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/index/file/knet/pipelines.py:146: [34mnote:(B[m          def get_pipeline(cls, user_settings: Any, index_settings: Any, selected: Any) -> Any(B[m
libs/ktem/ktem/index/file/graph/pipelines.py:13: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:19: [1m[31merror:(B[m Module (B[m[1m"ktem.index.file.pipelines"(B[m does not explicitly export attribute (B[m[1m"BaseFileIndexRetriever"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:55: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:59: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:76: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:98: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:109: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:110: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_graphrag_api_key"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:154: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:178: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:189: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:307: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:345: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:351: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:351: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:361: [1m[31merror:(B[m Call to untyped function (B[m[1m"check_graphrag_api_key"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:364: [1m[31merror:(B[m Call to untyped function (B[m[1m"_build_graph_search"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/pipelines.py:391: [1m[31merror:(B[m Call to untyped function (B[m[1m"plot_graph"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/base.py:56: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/base.py:62: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/base.py:62: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/base.py:65: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/base.py:65: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/base.py:68: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/base.py:68: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/base.py:86: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/base.py:99: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/base.py:113: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/base.py:129: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/manager.py:3: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/manager.py:23: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:29: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/manager.py:33: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:33: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/manager.py:72: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:72: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/manager.py:95: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:95: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/manager.py:111: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:128: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_delete"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/manager.py:143: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:143: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/manager.py:179: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:179: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/manager.py:184: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_index_types"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/manager.py:196: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/manager.py:199: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:20: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:38: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:38: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/index.py:39: [1m[31merror:(B[m Call to untyped function (B[m[1m"__init__"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:43: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Type"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/index.py:45: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"Type"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/index.py:48: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/index.py:49: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/index.py:51: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:85: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/index.py:110: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/index.py:147: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/index.py:165: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:165: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:199: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:199: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:238: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:238: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:273: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:273: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:308: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:308: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:319: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_admin_settings"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:328: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_resources"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:334: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:334: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:338: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_resources"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:342: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m of (B[m[1m"BaseVectorStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:343: [1m[31merror:(B[m Call to untyped function (B[m[1m"drop"(B[m of (B[m[1m"BaseDocumentStore"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:346: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:346: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/index.py:348: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_resources"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:349: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_indexing_cls"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:350: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_retriever_cls"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:351: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_file_index_ui_cls"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:352: [1m[31merror:(B[m Call to untyped function (B[m[1m"_setup_file_selector_ui_cls"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/index.py:354: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:359: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:364: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:364: [1m[31merror:(B[m Signature of (B[m[1m"get_user_settings"(B[m incompatible with supertype (B[m[1m"ktem.index.base.BaseIndex"(B[m  (B[m[33m[override](B[m
libs/ktem/ktem/index/file/index.py:364: [34mnote:(B[m      Superclass:(B[m
libs/ktem/ktem/index/file/index.py:364: [34mnote:(B[m          @classmethod(B[m
libs/ktem/ktem/index/file/index.py:364: [34mnote:(B[m          def get_user_settings(cls) -> dict[Any, Any](B[m
libs/ktem/ktem/index/file/index.py:364: [34mnote:(B[m      Subclass:(B[m
libs/ktem/ktem/index/file/index.py:364: [34mnote:(B[m          def get_user_settings(self) -> Any(B[m
libs/ktem/ktem/index/file/index.py:377: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:440: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/index.py:463: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/app.py:40: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:40: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:71: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/app.py:72: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/app.py:74: [1m[31merror:(B[m Call to untyped function (B[m[1m"register_extensions"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:75: [1m[31merror:(B[m Call to untyped function (B[m[1m"register_reasonings"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:76: [1m[31merror:(B[m Call to untyped function (B[m[1m"initialize_indices"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:78: [1m[31merror:(B[m Call to untyped function (B[m[1m"finalize"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:79: [1m[31merror:(B[m Call to untyped function (B[m[1m"finalize"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:84: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:84: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:86: [1m[31merror:(B[m Call to untyped function (B[m[1m"IndexManager"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:87: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_application_startup"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:95: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:95: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:109: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:109: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:136: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:146: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:146: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/app.py:157: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:157: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/app.py:163: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:163: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:166: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:166: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:169: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:169: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:172: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:172: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:175: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:211: [1m[31merror:(B[m Call to untyped function (B[m[1m"ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:213: [1m[31merror:(B[m Call to untyped function (B[m[1m"declare_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:214: [1m[31merror:(B[m Call to untyped function (B[m[1m"subscribe_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:215: [1m[31merror:(B[m Call to untyped function (B[m[1m"register_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:216: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_app_created"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:222: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:222: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:229: [1m[31merror:(B[m Call to untyped function (B[m[1m"declare_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:231: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:231: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:233: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_subscribe_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:236: [1m[31merror:(B[m Call to untyped function (B[m[1m"subscribe_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:238: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:238: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:240: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_register_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:243: [1m[31merror:(B[m Call to untyped function (B[m[1m"register_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:245: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:245: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:247: [1m[31merror:(B[m Call to untyped function (B[m[1m"_on_app_created"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:250: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_app_created"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:258: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:261: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:261: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:264: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:264: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:267: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:267: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:270: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:270: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:282: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:282: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:287: [1m[31merror:(B[m Call to untyped function (B[m[1m"render"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:289: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:289: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:294: [1m[31merror:(B[m Call to untyped function (B[m[1m"unrender"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:296: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:296: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:303: [1m[31merror:(B[m Call to untyped function (B[m[1m"declare_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:305: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:305: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:307: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_subscribe_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:310: [1m[31merror:(B[m Call to untyped function (B[m[1m"subscribe_public_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:312: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:312: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:314: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_register_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:317: [1m[31merror:(B[m Call to untyped function (B[m[1m"register_events"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:319: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/app.py:319: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/app.py:321: [1m[31merror:(B[m Call to untyped function (B[m[1m"_on_app_created"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/app.py:324: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_app_created"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:103: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:104: [1m[31merror:(B[m Call to untyped function (B[m[1m"__init__"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:112: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:114: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:114: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:130: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:131: [1m[31merror:(B[m Call to untyped function (B[m[1m"__init__"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:146: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:164: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:164: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:231: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:231: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:282: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:282: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:333: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_file_list"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:336: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_group_list"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:338: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:338: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:391: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:443: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:477: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:483: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:519: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:547: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:565: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:567: [1m[31merror:(B[m Call to untyped function (B[m[1m"delete_event"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:569: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:572: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:590: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:722: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:724: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_register_quick_uploads"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1035: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1035: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:1054: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1054: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1088: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1159: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1199: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1199: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1217: [1m[31merror:(B[m Call to untyped function (B[m[1m"is_arxiv_url"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1221: [1m[31merror:(B[m Call to untyped function (B[m[1m"download_arxiv_pdf"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1263: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1336: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1336: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1348: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1403: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1411: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1478: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1490: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1516: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/index/file/ui.py:1527: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1547: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1547: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1559: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1559: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1573: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1602: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1614: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1615: [1m[31merror:(B[m Call to untyped function (B[m[1m"__init__"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1617: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1619: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1624: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1624: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:1625: [1m[31merror:(B[m Call to untyped function (B[m[1m"default"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/ui.py:1650: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1665: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1668: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1691: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1692: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/ui.py:1735: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1735: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/ui.py:1742: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/ui.py:1742: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_promptui.py:9: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_promptui.py:9: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_promptui.py:28: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/kotaemon/tests/test_promptui.py:28: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/kotaemon/tests/test_promptui.py:37: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:11: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:26: [1m[31merror:(B[m Module (B[m[1m"ktem.index.file.pipelines"(B[m does not explicitly export attribute (B[m[1m"BaseFileIndexRetriever"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:58: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:67: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:70: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:108: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:118: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:125: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_embedding_func"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:130: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_llm_func"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:135: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:142: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:151: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:227: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:244: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:278: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:310: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:326: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_default_models_wrapper"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:354: [1m[31merror:(B[m Call to untyped function (B[m[1m"build_graphrag"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:390: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:410: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:421: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:438: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_default_models_wrapper"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:439: [1m[31merror:(B[m Call to untyped function (B[m[1m"build_graphrag"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:460: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:495: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:507: [1m[31merror:(B[m Call to untyped function (B[m[1m"_build_graph_search"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:512: [1m[31merror:(B[m Call to untyped function (B[m[1m"nano_graph_rag_build_local_query_context"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_pipelines.py:520: [1m[31merror:(B[m Call to untyped function (B[m[1m"plot_graph"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:11: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:26: [1m[31merror:(B[m Module (B[m[1m"ktem.index.file.pipelines"(B[m does not explicitly export attribute (B[m[1m"BaseFileIndexRetriever"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:60: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:69: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:72: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:110: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:120: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:127: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_embedding_func"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:132: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_llm_func"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:137: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:144: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:153: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:235: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:256: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:290: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:322: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:338: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_default_models_wrapper"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:366: [1m[31merror:(B[m Call to untyped function (B[m[1m"build_graphrag"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:402: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:422: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:433: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:450: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_default_models_wrapper"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:451: [1m[31merror:(B[m Call to untyped function (B[m[1m"build_graphrag"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:472: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:499: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:511: [1m[31merror:(B[m Call to untyped function (B[m[1m"_build_graph_search"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:516: [1m[31merror:(B[m Call to untyped function (B[m[1m"lightrag_build_local_query_context"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/lightrag_pipelines.py:519: [1m[31merror:(B[m Call to untyped function (B[m[1m"plot_graph"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/ui.py:15: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:26: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:31: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/ui.py:33: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:33: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/rerankings/ui.py:129: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:141: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:144: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/rerankings/ui.py:150: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/ui.py:152: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:244: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:258: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:277: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:277: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:287: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:311: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/rerankings/ui.py:326: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:333: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:372: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/rerankings/ui.py:385: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:25: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:52: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:54: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/setup.py:56: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:56: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/setup.py:138: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:138: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/setup.py:188: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:392: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/setup.py:401: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:6: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/resources/user.py:30: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:51: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:97: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:121: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:124: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/user.py:135: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:135: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/resources/user.py:181: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:262: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:286: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:287: [1m[31merror:(B[m Call to untyped function (B[m[1m"validate_username"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/user.py:292: [1m[31merror:(B[m Call to untyped function (B[m[1m"validate_password"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/user.py:315: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:343: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:343: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:353: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:392: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:406: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/user.py:407: [1m[31merror:(B[m Call to untyped function (B[m[1m"validate_username"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/user.py:413: [1m[31merror:(B[m Call to untyped function (B[m[1m"validate_password"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/user.py:431: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/report.py:5: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/chat/report.py:10: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/report.py:12: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/report.py:14: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/report.py:14: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/report.py:44: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/report.py:44: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/report.py:50: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/report.py:51: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/report.py:54: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/paper_list.py:9: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/paper_list.py:11: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/paper_list.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/paper_list.py:29: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/paper_list.py:30: [1m[31merror:(B[m Call to untyped function (B[m[1m"fetch_papers"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/paper_list.py:34: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/paper_list.py:34: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/paper_list.py:40: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/paper_list.py:40: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/demo_hint.py:8: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/demo_hint.py:10: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/demo_hint.py:12: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/demo_hint.py:12: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:17: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:19: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:21: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:21: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:38: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/chat_suggestion.py:41: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/chat_panel.py:26: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/chat_panel.py:28: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/chat_panel.py:28: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/chat_panel.py:51: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:24: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:29: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/ui.py:31: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:31: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/llms/ui.py:124: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:136: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:139: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/llms/ui.py:145: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/ui.py:147: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:243: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:257: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:276: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:276: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:286: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:310: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/llms/ui.py:325: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:332: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:332: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:371: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/llms/ui.py:380: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:11: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:11: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/ui.py:25: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:36: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:42: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/ui.py:44: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:44: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/ui.py:109: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:125: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:223: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:233: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/ui.py:238: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/ui.py:240: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:258: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:277: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:288: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:301: [1m[31merror:(B[m Call to untyped function (B[m[1m"info"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/ui.py:303: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/ui.py:313: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/ui.py:321: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:24: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:29: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/ui.py:31: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:31: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/embeddings/ui.py:127: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:139: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:142: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/embeddings/ui.py:148: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/ui.py:150: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:245: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:259: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:278: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:278: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:288: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:312: [1m[31merror:(B[m Call to untyped function (B[m[1m"format_description"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/embeddings/ui.py:327: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:334: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:373: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/embeddings/ui.py:386: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:6: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/settings.py:36: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:68: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:115: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:117: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:117: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/settings.py:127: [1m[31merror:(B[m Call to untyped function (B[m[1m"user_tab"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:129: [1m[31merror:(B[m Call to untyped function (B[m[1m"app_tab"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:130: [1m[31merror:(B[m Call to untyped function (B[m[1m"index_tab"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:131: [1m[31merror:(B[m Call to untyped function (B[m[1m"reasoning_tab"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:133: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:167: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:187: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:234: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:234: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/settings.py:253: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:256: [1m[31merror:(B[m Call to untyped function (B[m[1m"validate_password"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:277: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:277: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/settings.py:280: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_setting_item"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:287: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:287: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/settings.py:300: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_setting_item"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:307: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:307: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/settings.py:313: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_setting_item"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:321: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_setting_item"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:340: [1m[31merror:(B[m Call to untyped function (B[m[1m"render_setting_item"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:347: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:356: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:365: [1m[31merror:(B[m Call to untyped function (B[m[1m"component_names"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:368: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:368: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:375: [1m[31merror:(B[m Call to untyped function (B[m[1m"component_names"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/settings.py:394: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"list"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/settings.py:401: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:405: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:414: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/settings.py:424: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:5: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/login.py:29: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:31: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/login.py:33: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:33: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/login.py:39: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:39: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/login.py:55: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:62: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:62: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/login.py:77: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:77: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/login.py:88: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/login.py:88: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:7: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/chat/control.py:33: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:47: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:50: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:52: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:52: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/control.py:201: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:237: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/pages/chat/control.py:243: [1m[31merror:(B[m Unused (B[m[1m"type: ignore"(B[m comment  (B[m[33m[unused-ignore](B[m
libs/ktem/ktem/pages/chat/control.py:252: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:253: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_chat_history"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:259: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:271: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_chat_history"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:275: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:292: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_chat_history"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:299: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:326: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/control.py:379: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:388: [1m[31merror:(B[m Call to untyped function (B[m[1m"is_conv_name_valid"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:404: [1m[31merror:(B[m Call to untyped function (B[m[1m"load_chat_history"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/control.py:412: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:442: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:442: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:465: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/control.py:465: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/knet/knet_index.py:11: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/knet_index.py:12: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_admin_settings"(B[m of (B[m[1m"FileIndex"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/knet/knet_index.py:19: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/knet_index.py:19: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/knet/knet_index.py:22: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/knet_index.py:22: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/knet/knet_index.py:25: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/knet/knet_index.py:37: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/graph_index.py:10: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/graph_index.py:10: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/graph_index.py:13: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/graph_index.py:13: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/graph_index.py:16: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/graph_index.py:26: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/resources/__init__.py:3: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/resources/__init__.py:14: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/__init__.py:16: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:18: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/__init__.py:18: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/resources/__init__.py:20: [1m[31merror:(B[m Call to untyped function (B[m[1m"IndexManagement"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:23: [1m[31merror:(B[m Call to untyped function (B[m[1m"LLMManagement"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:26: [1m[31merror:(B[m Call to untyped function (B[m[1m"EmbeddingManagement"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:29: [1m[31merror:(B[m Call to untyped function (B[m[1m"RerankingManagement"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:33: [1m[31merror:(B[m Call to untyped function (B[m[1m"UserManagement"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/resources/__init__.py:35: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/resources/__init__.py:35: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/resources/__init__.py:57: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:11: [1m[31merror:(B[m Module (B[m[1m"ktem.db.models"(B[m does not explicitly export attribute (B[m[1m"engine"(B[m  (B[m[33m[attr-defined](B[m
libs/ktem/ktem/pages/chat/__init__.py:201: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:205: [1m[31merror:(B[m Call to untyped function (B[m[1m"on_building_ui"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:217: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:217: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/pages/chat/__init__.py:226: [1m[31merror:(B[m Call to untyped function (B[m[1m"ConversationControl"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:271: [1m[31merror:(B[m Call to untyped function (B[m[1m"ChatSuggestion"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:303: [1m[31merror:(B[m Call to untyped function (B[m[1m"ReportIssue"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:308: [1m[31merror:(B[m Call to untyped function (B[m[1m"HintPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:312: [1m[31merror:(B[m Call to untyped function (B[m[1m"PaperListPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:402: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:402: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/__init__.py:410: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:567: [1m[31merror:(B[m Call to untyped function (B[m[1m"select_conv"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:629: [1m[31merror:(B[m Call to untyped function (B[m[1m"toggle_delete"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:667: [1m[31merror:(B[m Call to untyped function (B[m[1m"toggle_delete"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:674: [1m[31merror:(B[m Call to untyped function (B[m[1m"toggle_delete"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:728: [1m[31merror:(B[m Call to untyped function (B[m[1m"toggle_delete"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:822: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:825: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:871: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:871: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:952: [1m[31merror:(B[m Call to untyped function (B[m[1m"new_conv"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:978: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:987: [1m[31merror:(B[m Call to untyped function (B[m[1m"get_recommended_papers"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:989: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:995: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1017: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1032: [1m[31merror:(B[m Call to untyped function (B[m[1m"select_conv"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/pages/chat/__init__.py:1051: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1073: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1134: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1140: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1140: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1154: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1154: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1166: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1166: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1168: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/__init__.py:1174: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/__init__.py:1264: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1287: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/pages/chat/__init__.py:1367: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/pages/chat/__init__.py:1382: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:13: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:13: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:17: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:17: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:20: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:20: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:42: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:54: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_or_create_collection_graph_id"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/nano_graph_index.py:62: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:13: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:13: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:17: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:17: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:20: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:20: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:23: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:42: [1m[31merror:(B[m Function is missing a type annotation for one or more arguments  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:54: [1m[31merror:(B[m Call to untyped function (B[m[1m"_get_or_create_collection_graph_id"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/index/file/graph/light_graph_index.py:62: [1m[31merror:(B[m Missing type parameters for generic type (B[m[1m"dict"(B[m  (B[m[33m[type-arg](B[m
libs/ktem/ktem/main.py:21: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/main.py:42: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/main.py:42: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
libs/ktem/ktem/main.py:53: [1m[31merror:(B[m Call to untyped function (B[m[1m"LoginPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/main.py:61: [1m[31merror:(B[m Call to untyped function (B[m[1m"ChatPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/main.py:103: [1m[31merror:(B[m Call to untyped function (B[m[1m"ResourcesTab"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/main.py:112: [1m[31merror:(B[m Call to untyped function (B[m[1m"SettingsPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/main.py:125: [1m[31merror:(B[m Call to untyped function (B[m[1m"SetupPage"(B[m in typed context  (B[m[33m[no-untyped-call](B[m
libs/ktem/ktem/main.py:127: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/main.py:133: [1m[31merror:(B[m Function is missing a type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/main.py:202: [1m[31merror:(B[m Function is missing a return type annotation  (B[m[33m[no-untyped-def](B[m
libs/ktem/ktem/main.py:202: [34mnote:(B[m Use (B[m[1m"-> None"(B[m if function does not return a value(B[m
[1m[31mFound 1528 errors in 162 files (checked 246 source files)(B[m

codespell................................................................[42mPassed[m
