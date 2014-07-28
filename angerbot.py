#adding a comment to amke a change tot hge fiel

import gobject
import pygst
pygst.require('0.10')
gobject.threads_init()
import gst
import time
import sys
import os
import random
import logging

from collections import defaultdict

logging.basicConfig(format='%(asctime)s:%(message)s',filename='angerbot.log',level=logging.DEBUG)
#logging.basicConfig(filename='angerbot.log',level=logging.DEBUG)
filePath =os.path.dirname(os.path.abspath(__file__))
hmmPath = filePath + '/language_model'
dictPath = hmmPath + '/4040.dic'
lmPath = hmmPath + '/4040.lm'
corpusPath = hmmPath + '/4040.corpus'

nearMisses = defaultdict(list)
matches = defaultdict(list)
fails = defaultdict(list)

class Phrase:

	def __init__(self, phrase, score, response):
		self.phrase = phrase.upper()
		self.phraseBag = set(self.phrase.split(" "))
		self.scoreThreshold = score
		self.responseFilePath = response

	def match(self, phraseToCompare):
		compareBag = set(phraseToCompare.split(" "))
		intersectionBag = self.phraseBag.intersection(compareBag)
		originalPhraseLength = len(self.phraseBag)
		comparePhraseLength = len(compareBag)
		self.numOfMatchedWords = len(intersectionBag)
		self.numOfUnrecognisedWords = originalPhraseLength - self.numOfMatchedWords
		self.numOfUnmatchedWords = comparePhraseLength - self.numOfMatchedWords
		self.percentageOfRecognisedWords = self.percent(self.numOfMatchedWords, originalPhraseLength)
		self.percentageOfMatchedWords = self.percent(self.numOfMatchedWords, comparePhraseLength)

		self.wordErrorRate = self.percent((self.numOfUnrecognisedWords + self.numOfUnmatchedWords), (originalPhraseLength + comparePhraseLength))
		
		return self.wordErrorRate;

	def percent(self, actual, total):
		percent = (float(actual) / total) * 100
		return percent

class AngerBot:


	def __init__(self, phrases):
		self.phrases = phrases
		print self.phrases

	def asr_result(self, asr, text, uttid):
		self.pipeline.set_state(gst.STATE_PAUSED)
		logging.info( "processing result " + text)
		lowestWordErrorRate = sys.float_info.max
		for phrase in self.phrases:
			wordErrorRate = phrase.match(text)
			if wordErrorRate < lowestWordErrorRate:
				lowestWordErrorRate = wordErrorRate
				topMatch = phrase
		try:
			if lowestWordErrorRate <= topMatch.scoreThreshold:
				matches[topMatch.phrase].append(topMatch.wordErrorRate)
				logging.info( "matched %s WER: %f" % (topMatch.phrase, topMatch.wordErrorRate))
				# play the right sound for the phrase
				os.system('aplay ' + topMatch.responseFilePath)
			elif lowestWordErrorRate <= (topMatch.scoreThreshold + (topMatch.scoreThreshold/2)):
				nearMisses[topMatch.phrase].append(topMatch.wordErrorRate)
				logging.info( "near miss %s, WER: %f" % (topMatch.phrase, topMatch.wordErrorRate) )
				# play a randomly selected rude phrase
				os.system('aplay ' + self.random_near_miss_phrase())
			else:
				fails[topMatch.phrase].append(topMatch.wordErrorRate)
				logging.info( "no match" )
				#ignore
		except NameError:
			logging.error( "Unable to match with any phrases" )
		self.pipeline.set_state(gst.STATE_PLAYING)

	def random_near_miss_phrase(self):
		randomNumber = random.randrange(1,4)
		return filePath + '/near_misses/nearmiss%d.wav' % randomNumber

	def start(self, hmm, lm, dic):

		self.pipeline = gst.parse_launch('alsasrc device=plughw:1,0 ! audioconvert ! audioresample '
				                                 + '! vader name=vad auto_threshold=true '
				                                 + '! pocketsphinx name=asr ' 
				                                 + '! fakesink')
		logging.info( "created pipeline" )

		# instantiate pocketsphinx
		asr = self.pipeline.get_by_name('asr')
		logging.info( "instatiated asr with lm: " + lm + " dict: " + dic + " hmm " + hmm )

		# call asr_result on result
		asr.connect('result', self.asr_result)
		logging.info( "connected asr result" )

		# initialise the speech recogniser
		asr.set_property('dict', dic)
		asr.set_property('lm', lm)
		asr.set_property('hmm', hmm)
		asr.set_property('configured', True)
		logging.info( "asr configured property set to true" )

		# to start vader

		vader = self.pipeline.get_by_name('vad')
		vader.set_property('silent', True)
		logging.info( "vader instatiated" )

		self.pipeline.set_state(gst.STATE_PLAYING)
		logging.info( "Pipeline set to play" )
		
		self.listening = True

		#ready to start listening, play startup beep
		os.system('aplay ' + filePath + "/startup-beep.wav")

		# loop in order to prevent the app from exiting
		while self.listening:
			time.sleep(1)

			
		

phrases = list()
f = open(corpusPath)
try:
    for line in f:
		phrase = line.strip()
		if len(phrase) > 0:
			parts = phrase.split(",")
			phrases.append(Phrase(parts[0], int(parts[1].strip()), filePath + "/" + parts[2].strip()))
finally:
    f.close()

bot = AngerBot(phrases)
bot.start(hmmPath, lmPath, dictPath)

