
from signal import Signal
import json


class Object:
	def __init__(self):
		self.changed = Signal()
		self.deleted = Signal()
		self.active = True
		self.id = None
		
	def delete(self):
		self.active = False
		self.deleted.emit()
		self.changed.emit()
		
	def load(self, data):
		self.id = data["id"]
	
	def save(self):
		return {"id": self.id}


class Node(Object):
	def __init__(self, x=0, y=0):
		super().__init__()
		self.positionChanged = Signal()
		
		self.x = x
		self.y = y
		self.label = ""
		self.input = []
		self.output = []
		
	def move(self, x, y):
		self.x = x
		self.y = y
		self.positionChanged.emit()
		self.changed.emit()
		
	def load(self, data):
		super().load(data)
		self.x = data["x"]
		self.y = data["y"]
		self.label = data["label"]
	
	def save(self):
		data = super().save()
		data["x"] = self.x
		data["y"] = self.y
		data["label"] = self.label
		return data

	def __repr__(self):
		return json.dumps(self.save())


class Place(Node):
	def __init__(self, x=0, y=0):
		super().__init__(x, y)
		self.tokens = 0


class Transition(Node):
	pass


class Arrow(Node):
	def __init__(self, place, transition):
		super().__init__()
		self.place = place
		self.transition = transition

	def load(self, data):
		super().load(data)
		self.place = data["place"]
		self.transition = data["transition"]

	def save(self):
		data = super().save()
		data["place"] = self.place
		data["transition"] = self.place


class PetriNet:
	def __init__(self):
		self.changed = Signal()

		self.placeAdded = Signal()
		self.transitionAdded = Signal()
		self.DependencyAdded = Signal()
		self.OutputAdded = Signal()
		
		self.nextPlaceId = 0
		self.nextTransitionId = 0
		self.nextDependencyId = 0
		self.nextOutputId = 0

		self.places = {}
		self.transitions = {}
		self.dependencies = {}
		self.outputs = {}

	def __repr__(self):
		return json.dumps(self.save())
			
	def load(self, data):
		def getNextId(lst):
			return max(map(lambda x: x.id, lst))

		nextPlaceId = getNextId(data["places"])
		nextTransitionId = getNextId(data["transitions"])

		for place in data["places"]:
			obj = Place()
			obj.load(place)
			self.addPlace(obj)
		for transition in data["transitions"]:
			obj = Transition()
			obj.load(transition)
			self.addTransition(obj)
		for dependency in data["dependencies"]:
			self.addArrowPlaceToTransition(dependency["place"], dependency["transition"])
		for output in data["outputs"]:
			self.addArrowTransitionToPlace(dependency["transition"], dependency["place"])

		
	def save(self):
		def safeIfActive(lst):
			return map(lambda x: x.save(), filter(lambda x: x.active, lst))

		places = safeIfActive(self.places.values())
		transitions = safeIfActive(self.transitions.values())

		dependencies = []
		outputs = []
		for transition in self.transitions.values():
			for outputId in transition.outputs:
				outputs.append({
					"transition": transition.id,
					"place": outputId})
			for inputId in transition.inputs:
				dependencies.append({
					"transition": transition.id,
					"place": inputId})

		data = {
			"places": places,
			"transitions": transitions,
			"dependencies": dependencies,
			"outputs": outputs
		}
		return data

	def addPlace(self, place):
		if place.id is None:
			place.id = self.nextPlaceId
			self.nextPlaceId += 1
			
		place.changed.connect(self.changed.emit)
		
		self.places[place.id] = place
		self.placeAdded.emit(place)
		self.changed.emit()

	def addTransition(self, transition):
		if transition.id is None:
			transition.id = self.nextTransitionId
			self.nextTransitionId += 1
			
		transition.changed.connect(self.changed.emit)
		
		self.transitions[transition.id] = transition
		self.transitionAdded.emit(transition)
		self.changed.emit()

	def getDependency(self, place, transition):
		results = filter(
			lambda x: x.place == place and x.transition == transition,
			self.dependencies.values())
		if results:
			return results[0]
		return None

	def getOutput(self, place, transition):
		results = filter(
			lambda x: x.place == place and x.transition == transition,
			self.outputs.values())
		if results:
			return results[0]
		return None

	def addDependency(self, placeId, transitionId):
		self.addDependency(Arrow(placeId, transitionId))

	def addDependency(self, dependency):
		previous = self.getDependency(dependency.place, dependency.transition)
		if previous:
			return previous

		if dependency.id is None:
			dependency.id = self.nextDependencyId
			self.nextDependencyId += 1

		dependency.changed.connect(self.changed.emit)
		self.dependencies[dependency.id] = dependency
		self.dependencyAdded.emit(dependency)
		self.changed.emit()

	def addOutput(self, placeId, transitionId):
		self.addOutput(Arrow(placeId, transitionId))

	def addOutput(self, output):
		previous = self.getOutput(output.place, output.transition)
		if previous:
			return previous

		if output.id is None:
			output.id = self.nextOutputId
			self.nextOutputId += 1

		output.changed.connect(self.changed.emit)
		self.outputs[output.id] = output
		self.outputAdded.emit(output)
		self.changed.emit()

	def addArrowPlaceToTransition(self, placeId, transitionId):
		output = self.places[placeId].output
		input = self.transitions[transitionId].input
		if transitionId not in output:
			output.append(transitionId)
		if placeId not in input:
			input.append(placeId)

	def addArrowTransitionToPlace(self, transitionId, placeId):
		output = self.transitions[transitionId].output
		input = self.places[placeId].input
		if placeId not in output:
			output.append(placeId)
		if transitionId not in input:
			input.append(transitionId)

	def removeArrowPlaceToTransition(self, placeId, transitionId):
		output = self.places[placeId].output
		input = self.transitions[transitionId].input
		if transitionId in output:
			output.remove(transitionId)
		if placeId in input:
			input.remove(placeId)

	def removeArrowTransitionToPlace(self, placeId, transitionId):
		output = self.transitions[transitionId].output
		input = self.places[placeId].input
		if placeId in output:
			output.remove(placeId)
		if transitionId in input:
			input.remove(transitionId)


class Project:
	def __init__(self):
		self.filenameChanged = Signal()
		self.unsavedChanged = Signal()

		self.net = PetriNet()
		self.net.changed.connect(self.setUnsaved)
		self.filename = None
		self.unsaved = False

	def setFilename(self, filename):
		if self.filename != filename:
			self.filename = filename
			self.filenameChanged.emit()

	def setUnsaved(self, unsaved=True):
		if self.unsaved != unsaved:
			self.unsaved = unsaved
			self.unsavedChanged.emit()

	def load(self, filename):
		with open(filename) as f:
			data = json.load(f)
		self.net.load(data)
		
		self.setFilename(filename)
		self.setUnsaved(False)

	def save(self, filename):
		data = self.net.save()
		with open(filename, "w") as f:
			json.dump(data, f, indent="\t")
		
		self.setFilename(filename)
		self.setUnsaved(False)
