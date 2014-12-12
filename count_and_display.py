''' Display an ordered list of frequencies
	See post: https://carlyscodesnippets.wordpress.com/2014/10/02/sort-a-counter-object/
'''

from collections import Counter
from operator import itemgetter


def count_and_display(mylist):
	freq = Counter(mylist)
	
	counts = []
	for k,v in freq.items():
		counts.append((k,v))
	
	counts.sort(key = itemgetter(1), reverse = True)
	
	percents = []
	for k,v in counts:
		percents.append(round(float(v)/ len(mylist), 5))
	
	for count, p in zip(counts, percents):
		print "%s: %d, ~%.2f%%" %(count[0], count[1], p)