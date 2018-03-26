from . import util
import pdb


class Sample(object):
    def __init__(self, address, distribution, value, log_prob=0, controlled=False, observed=False):
        self.address = address
        self.distribution = distribution
        if distribution is None:
            self.address_suffixed = address
        else:
            self.address_suffixed = address + distribution.address_suffix
        self.value = util.to_variable(value)
        self.controlled = controlled
        self.observed = observed
        self.log_prob = log_prob
        self.lstm_input = None
        self.lstm_output = None

    def __repr__(self):
        return 'Sample(controlled:{}, observed:{}, address_suffixed:{}, distribution:{}, value:{})'.format(
            self.controlled,
            self.observed,
            self.address_suffixed,
            str(self.distribution),
            str(self.value)
        )

    def cuda(self, device=None):
        if self.value is not None:
            self.value = self.value.cuda(device)
        # self.distribution.cuda(device)

    def cpu(self):
        if self.value is not None:
            self.value = self.value.cpu()
        # self.distribution.cpu()


class Trace(object):
    def __init__(self):
        self.observes_variable = None
        self.observes_embedding = None
        self.samples = []  # controlled
        self.samples_uncontrolled = []
        self.samples_observed = []
        # these two always combine to form self.samples
        self.samples_fresh = []
        self.samples_stale = []
        self._samples_all = []
        self._resampled = None
        self.result = None
        self.log_prob = 0
        self.log_p_obs = 0
        self.log_p_fresh = 0
        self.log_p_stale = 0

        self.length = 0
        self.length_controlled = 0

    def __repr__(self):
        return 'Trace(controlled:{}, uncontrolled:{}, observed:{}, log_prob:{})'.format(len(self.samples), len(self.samples_uncontrolled), len(self.samples_observed), float(self.log_prob))

    def _find_last_sample(self, address):
        indices = [i for i, sample in enumerate(self._samples_all) if sample.address == address]
        if len(indices) == 0:
            return None
        else:
            return max(indices)

    def log_fresh(self):
        log_p = 0
        for sample in self.samples:
            log_p += sample.log_prob
        return log_p

    def log_y(self):
        log_p = 0
        for sample in self.samples_observed:
            log_p += sample.log_prob
        return log_p
    def addresses(self):
        return '; '.join([sample.address for sample in self.samples])

    def addresses_suffixed(self):
        return '; '.join([sample.address_suffixed for sample in self.samples])

    def end(self, result):
        self.result = result
        self.samples = [s for s in self._samples_all if s.controlled]
        self.samples_uncontrolled = [s for s in self._samples_all if (not s.controlled) and (not s.observed)]
        self.samples_observed = [s for s in self._samples_all if s.observed]


        self.log_prob = util.to_variable(sum([s.log_prob for s in self._samples_all if s.controlled or s.observed])).view(-1)
        self.log_p_obs = util.to_variable(sum([s.log_prob for s in self.samples_observed])).view(-1)
        try:
            self.log_p_stale = util.to_variable(sum([s.log_prob for s in self.samples_stale]) + self._resampled.log_prob).view(-1)
            self.log_p_fresh = util.to_variable(sum([s.log_prob for s in self.samples_fresh])).view(-1)
        except:
            None

        #  pdb.set_trace()
        self.observes_variable = util.pack_observes_to_variable([s.value for s in self.samples_observed])
        self.length = len(self.samples)

    def add_sample(self, sample, replace=False, fresh=True):
        if fresh != True and sample.observed == False:
            self.samples_stale.append(sample)
        if fresh == True and sample.observed == False:
            self.samples_fresh.append(sample)
        if replace:
            i = self._find_last_sample(sample.address)
            if i is not None:
                self._samples_all[i] = sample
                return
        self._samples_all.append(sample)

    def cuda(self, device=None):
        if self.observes_variable is not None:
            self.observes_variable = self.observes_variable.cuda(device)
        if self.observes_embedding is not None:
            self.observes_embedding = self.observes_embedding.cuda(device)
        for sample in self._samples_all:
            sample.cuda(device)

    def cpu(self):
        if self.observes_variable is not None:
            self.observes_variable = self.observes_variable.cpu()
        if self.observes_embedding is not None:
            self.observes_embedding = self.observes_embedding.cpu()
        for sample in self._samples_all:
            sample.cpu()
