from otree.api import *
import random


class C(BaseConstants):
    NAME_IN_URL = 'LivePagePoging1'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    STATES = ['X', 'Y']


class Subsession(BaseSubsession):
    def creating_session(subsession):
        subsession.group_randomly(fixed_id_in_group=True)


class Group(BaseGroup):
    true_state = models.StringField(
        choices=C.STATES,
    )


class Player(BasePlayer):
    message_sent = models.StringField(
        choices=C.STATES,
        blank=True
    )
    believed_state = models.StringField(
        choices=C.STATES,
        blank=True
    )
    points = models.IntegerField(initial=0)  # New field for tracking points

    @property
    def is_player1(self):
        return self.id_in_group == 1

    def get_payoff(self, true_state, p1_choice, p2_choice):
        payoff_matrix = {
            'X': {  # When true state is X
                ('X', 'X'): (20, 20),  # A, C
                ('X', 'Y'): (10, 10),  # A, D
                ('Y', 'X'): (10, 10),  # B, C
                ('Y', 'Y'): (0, 0),    # B, D
            },
            'Y': {  # When true state is Y
                ('X', 'X'): (10, 0),   # A, C
                ('X', 'Y'): (0, 10),   # A, D
                ('Y', 'X'): (20, 10),  # B, C
                ('Y', 'Y'): (10, 20),  # B, D
            }
        }
        
        payoffs = payoff_matrix[true_state][(p1_choice, p2_choice)]
        return payoffs[0] if self.is_player1 else payoffs[1]


# PAGES
class WaitForPairing(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        group.true_state = random.choice(C.STATES)


class Game(Page):
    @staticmethod
    def live_method(player: Player, data):
        group = player.group

        if data.get('type') == 'send_message':
            if player.is_player1:
                message = data.get('message')
                player.message_sent = message
                return {
                    player.id_in_group: {
                        'type': 'show_belief_input'
                    },
                    player.get_others_in_group()[0].id_in_group: {
                        'type': 'received_message',
                        'message': message
                    }
                }

        elif data.get('type') == 'submit_belief':
            player.believed_state = data.get('belief')
            return {
                player.id_in_group: {
                    'type': 'belief_submitted'
                }
            }

        elif data.get('type') == 'load' and player.is_player1:
            return {
                player.id_in_group: {
                    'type': 'true_state',
                    'state': group.true_state
                }
            }

    @staticmethod
    def js_vars(player: Player):
        return dict(
            is_player1=player.is_player1,
            round_number=player.round_number,
        )


class WaitForResults(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        p1 = group.get_player_by_id(1)
        p2 = group.get_player_by_id(2)
        
        # Calculate points for both players
        p1.points = p1.get_payoff(
            group.true_state,
            p1.message_sent,
            p2.believed_state
        )
        
        p2.points = p2.get_payoff(
            group.true_state,
            p1.message_sent,
            p2.believed_state
        )
        
        # Set payoffs (if you want to use oTree's built-in payoff system)
        p1.payoff = p1.points
        p2.payoff = p2.points


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'true_state': player.group.true_state,
            'points': player.points,
            'total_points': sum([p.points for p in player.in_all_rounds()]),
            'p1_message': player.group.get_player_by_id(1).message_sent,
            'p2_belief': player.group.get_player_by_id(2).believed_state
        }


page_sequence = [WaitForPairing, Game, WaitForResults, Results]
