"""Resumable serial generation; never cancels or clears the shared queue."""
import kit
for context in ['wall-03','wall-01','wall-02','wall-04','wall-05']:
 for variant in ['a','b','c']:
  kit.generate(context,variant)
