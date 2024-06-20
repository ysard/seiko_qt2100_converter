run:
	python -m seiko_converter -i "./data/seiko_qt2100_A10S_timestamped.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_A10S.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_B1S_1.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_B1S_2.raw" -g --csv -d
	#python -m seiko_converter -i "./data/seiko_qt2100_999999.raw" -g --csv -d

clean:
	@rm *.csv *.pdf
