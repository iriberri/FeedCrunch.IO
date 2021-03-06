#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import URLValidator
from django.http import HttpResponse

from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from feedcrunch.models import Post
from feedcrunch.models import FeedUser
from feedcrunch.models import Tag
from feedcrunch.models import Country
from feedcrunch.models import RSSFeed
from feedcrunch.models import RSSFeed_Sub
from feedcrunch.models import RSSArticle_Assoc

from feedcrunch import tasks

from oauth.twitterAPI import TwitterAPI
from oauth.facebookAPI import FacebookAPI
from oauth.linkedinAPI import LinkedInAPI
from oauth.slackAPI import SlackAPI

import datetime
import unicodedata
import feedparser

from functions.ap_style import format_title
from functions.check_admin import check_admin_api
from functions.check_social_network import auto_format_social_network
from functions.clean_html import clean_html
from functions.data_convert import str2bool
from functions.date_manipulation import get_N_time_period
from functions.feed_validation import validate_feed
from functions.time_funcs import get_timestamp


def mark_RSSArticle_Assoc_as_read(RSSArticle_AssocID, user):
    RSSArticle_Assoc_QuerySet = RSSArticle_Assoc.objects.filter(id=RSSArticle_AssocID, user=user)

    if not RSSArticle_Assoc_QuerySet.exists():
        raise Exception("The given RSSArticle_Assoc (id = '" + str(
            RSSArticle_AssocID) + "') with the given user (username = " + user.username + ") doesn't exist.")

    RSSArticle_Assoc_obj = RSSArticle_Assoc_QuerySet[0]

    RSSArticle_Assoc_obj.marked_read = True
    RSSArticle_Assoc_obj.save()


class UsernameValidationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):

        payload = dict()

        try:
            username = request.POST.get('username')
            payload["username"] = username

            if username == None:
                raise Exception("Username not provided")

            else:
                username = username.lower()  # Make it Lowercase
                payload["available"] = not FeedUser.objects.filter(username=username).exists()
                payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "Username Validation"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class RSSFeedValidationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        payload = dict()

        try:
            rssfeed = request.POST.get('rssfeed')

            if rssfeed == None:
                raise Exception("Link for the RSS Feed not provided")

            else:
                payload["rssfeed"] = rssfeed

                rssfeed_queryset = RSSFeed.objects.filter(link=rssfeed)

                if rssfeed_queryset.exists():
                    if RSSFeed.objects.filter(link=rssfeed, rel_sub_feed_assoc__user=request.user):
                        payload["valid"] = False
                        payload["error"] = "You already subscribed to this RSS Feed"
                    else:
                        payload["valid"] = True
                        payload["title"] = rssfeed_queryset[0].title

                else:
                    rss_data = feedparser.parse(rssfeed)

                    if validate_feed(rss_data):
                        payload["valid"] = True
                        payload["title"] = clean_html(rss_data.feed.title)

                    else:
                        payload["valid"] = False
                        payload["error"] = "The RSS Feed is not valid. Please check your link"

                payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "RSS Feed Validation"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class OPMLManagementView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    def get(self, request):
        try:
            return HttpResponse(request.user.export_opml(), content_type='text/xml')

        except Exception as e:
            payload = dict()
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["operation"] = "Export OPML"
            payload["timestamp"] = get_timestamp()
            return Response(payload)

    def post(self, request, filename=''):

        payload = dict()

        try:
            check_passed = check_admin_api(request.user)

            if check_passed != True:
                raise Exception(check_passed)

            if not 'opml_file' in request.data:
                raise Exception("opml_file not received")

            opml_file = request.data["opml_file"].read().decode('iso-8859-1').encode('ascii', 'ignore').replace("  ",
                                                                                                                " ")

            payload["feed_errors"] = request.user.load_opml(opml_file)

            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "OPML Import"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class UserSocialNetworkStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, social_network=None):

        payload = dict()

        try:
            social_network = auto_format_social_network(social_network)

            payload["success"] = True
            payload["username"] = request.user.username
            payload["social_network"] = social_network
            payload["status"] = request.user.is_social_network_activated(network=social_network)

        except Exception as e:
            payload["success"] = False
            payload["error"] = "FC_API.UserSocialNetworkStatusView() - An error occurred in the process: %s" % str(e)

        payload["operation"] = "User Social_Network Status"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class UnLinkUserSocialNetworkView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, social_network=None):

        payload = dict()

        try:
            social_network = auto_format_social_network(social_network)

            request.user.reset_social_network_credentials(network=social_network)

            payload["success"] = True
            payload["username"] = request.user.username
            payload["social_network"] = social_network

            if social_network == "twitter":
                payload["auth_url"] = TwitterAPI.get_authorization_url(request)
            elif social_network == "facebook":
                payload["auth_url"] = FacebookAPI.get_authorization_url()
            elif social_network == "linkedin":
                payload["auth_url"] = LinkedInAPI.get_authorization_url()
            elif social_network == "slack":
                payload["auth_url"] = SlackAPI.get_authorization_url()
            else:
                raise Exception("'social_network' (" + social_network + ") is not supported.")

        except Exception as e:
            payload["success"] = False
            payload["error"] = "FC_API.UnLinkUserSocialNetworkView() - An error occured in the process:  " + str(e)

        payload["operation"] = "Unlink User Social_Network"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class UserStatsSubscribersView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        payload = dict()

        try:

            payload["success"] = True
            payload["username"] = request.user.username

            first_subscribers_record_date = datetime.datetime(2017, 3, 29).date()

            if (first_subscribers_record_date > request.user.date_joined.replace(tzinfo=None).date()):
                date_array = get_N_time_period(21, 14, max_date=first_subscribers_record_date)
            else:
                date_array = get_N_time_period(21, 14, max_date=request.user.date_joined.replace(tzinfo=None).date())

            today = datetime.datetime.now().date()

            ticks = []
            data = []

            for i, d in enumerate(date_array):
                delta = (today - d.date()).days
                data.append([i, request.user.get_user_subscribers_count(delta)])
                ticks.append([i, d.strftime("%d. %b")])

            payload["data"] = data
            payload["ticks"] = ticks

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "Get User Subscriber Stats"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class UserStatsPublicationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        payload = dict()

        try:
            payload["success"] = True
            payload["username"] = request.user.username

            date_array = get_N_time_period(21)

            ticks = []
            data = []

            for i, d in enumerate(date_array):
                count = request.user.rel_posts.filter(when__year=d.year, when__month=d.month, when__day=d.day).count()
                data.append([i, count])
                ticks.append([i, d.strftime("%d. %b")])

            payload["data"] = data
            payload["ticks"] = ticks

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "Get User Publication Stats"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class Tags(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        payload = dict()

        try:
            tags = Tag.objects.all().order_by('name')

            payload["tags"] = [tag.name for tag in tags]

            payload["success"] = True
            payload["username"] = request.user.username

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "Get All Tags"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class RSSFeedView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        payload = dict()

        try:
            title = unicodedata.normalize('NFC', request.POST['rssfeed_title'])
            link = unicodedata.normalize('NFC', request.POST['rssfeed_link'])

            rssfeed_queryset = RSSFeed.objects.filter(link=link)

            if not rssfeed_queryset.exists():
                tmp_rssfeed = RSSFeed.objects.create(title=title, link=link)
                tasks.check_rss_feed.delay(rss_id=tmp_rssfeed.id)

                old_articles = None

            else:
                tmp_rssfeed = rssfeed_queryset[0]
                old_articles = RSSArticle_Assoc.objects.filter(article__rssfeed=tmp_rssfeed)

            tmp_sub = RSSFeed_Sub.objects.create(user=request.user, feed=tmp_rssfeed, title=title)

            if ((old_articles is not None) and (old_articles.count() > 0)):
                for article in old_articles:
                    article.subscription = tmp_sub
                    article.save()

            payload["RSSFeed_Sub_ID"] = str(tmp_sub.id)
            payload["RSSFeedID"] = str(tmp_rssfeed.id)
            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "subscribe to RSS Feed"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class RSSFeedSubView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, RSSFeed_SubID=None):

        payload = dict()

        try:
            RSSFeed_SubID = int(unicodedata.normalize('NFC', RSSFeed_SubID))
            if type(RSSFeed_SubID) is not int or RSSFeed_SubID < 1:
                raise Exception("RSSFeed_SubID parameter is not valid")

            payload["username"] = request.user.username

            RSSFeed_Sub_queryset = RSSFeed_Sub.objects.filter(id=RSSFeed_SubID, user=request.user)

            if RSSFeed_Sub_queryset.count() == 0:
                raise Exception(
                    "RSSFeed_Sub (id: " + RSSFeed_SubID + ") does not exist for the user: " + request.user.username)

            RSSFeed_Sub_obj = RSSFeed_Sub_queryset[0]

            title = unicodedata.normalize('NFC', request.POST['rssfeed_title'])

            if title == "":
                raise Exception("Title and/or Link is/are missing")

            RSSFeed_Sub_obj.title = title

            RSSFeed_Sub_obj.save()

            payload["success"] = True
            payload["RSSFeed_SubID"] = str(RSSFeed_SubID)

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["RSSFeed_SubID"] = str(RSSFeed_SubID)

        payload["operation"] = "modify RSSFeed"
        payload["timestamp"] = get_timestamp()
        return Response(payload)

    def delete(self, request, RSSFeed_SubID=None):

        payload = dict()

        try:
            RSSFeed_SubID = int(unicodedata.normalize('NFC', RSSFeed_SubID))
            if type(RSSFeed_SubID) is not int or RSSFeed_SubID < 1:
                raise Exception("RSSFeed_SubID parameter is not valid")

            payload["username"] = request.user.username

            RSSFeed_Sub_queryset = RSSFeed_Sub.objects.filter(id=RSSFeed_SubID, user=request.user)

            if RSSFeed_Sub_queryset.count() == 0:
                raise Exception(
                    "RSSFeed_Sub (id: " + RSSFeed_SubID + ") does not exist for the user: " + request.user.username)

            RSSFeed_Sub_queryset[0].delete()

            payload["success"] = True
            payload["RSSFeed_SubID"] = str(RSSFeed_SubID)

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["RSSFeed_SubID"] = str(RSSFeed_SubID)

        payload["operation"] = "delete RSS Feed"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class IsArticleExistingView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        payload = dict()

        try:
            user = request.user

            if user.is_superuser and 'posting_user' in request.GET:
                tmp_username = unicodedata.normalize('NFC', request.GET['posting_user'])

                try:
                    user = FeedUser.objects.get(username=tmp_username)

                except ObjectDoesNotExist:
                    raise Exception("The Provided posting_user ('" + tmp_username + "') does not exist")

            article_link = unicodedata.normalize('NFC', request.GET['link'])

            if article_link[:7] == "http://":
                article_link_base = article_link[7:]
            elif article_link[:8] == "https://":
                article_link_base = article_link[8:]
            elif article_link[:2] == "//":
                article_link_base = article_link[2:]
            else:
                raise Exception("The link provided is invalid (http/https missing): " + article_link)

            if article_link_base[-1:] == "/":
                article_link_base = article_link_base[:-1]

            link_http_slash = "http://" + article_link_base + "/"
            link_https_slash = "https://" + article_link_base + "/"
            link_http_noslash = "http://" + article_link_base
            link_https_noslash = "https://" + article_link_base

            links = [
                link_http_slash,
                link_https_slash,
                link_http_noslash,
                link_https_noslash
            ]

            payload["exists"] = False
            payload["username"] = user.username

            for art_link in links:
                query_set = Post.objects.filter(link=art_link, user=user)
                if query_set.exists():
                    payload["exists"] = True
                    payload["post_data"] = {
                        'id': query_set[0].id,
                        'title': query_set[0].title,
                        'link': query_set[0].link
                    }
                    break

            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "Get Article Exists"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


################### NEED TO CHECK AUTHENTICATION PROCESS ###################

class ArticleView(APIView):

    def get(self, request):
        payload = dict()
        payload["success"] = True
        return Response(payload)

    def post(self, request, apikey=""):

        payload = dict()

        try:
            if apikey == "":
                check_passed = check_admin_api(request.user)

                if not check_passed:
                    raise Exception(check_passed)

                user = request.user

            else:
                try:
                    user = FeedUser.objects.filter(apikey=apikey)[:1][0]
                except IndexError:
                    raise Exception("The apikey Used is not Valid")

                if user.is_superuser and 'posting_user' in request.POST:
                    tmp_username = unicodedata.normalize('NFC', request.POST['posting_user'])
                    try:
                        user = FeedUser.objects.get(username=tmp_username)
                    except ObjectDoesNotExist:
                        raise Exception("The Provided posting_user `%s` does not exist" % tmp_username)

            payload["username"] = user.username

            if 'article_id' in request.POST:
                RSSArticle_Assoc_id = unicodedata.normalize('NFC', request.POST['article_id'])
                RSSArticle_Assoc_QuerySet = RSSArticle_Assoc.objects.filter(id=RSSArticle_Assoc_id, user=user)

                if not RSSArticle_Assoc_QuerySet.exists():
                    _err = "The given RSSArticle (id: %d) with the given username `%s`doesn't exist." % (
                        RSSArticle_Assoc_id,
                        user.username
                    )
                    raise Exception(_err)

                RSSArticle_Assoc_obj = RSSArticle_Assoc_QuerySet[0]

            else:
                RSSArticle_Assoc_id = -1

            title = unicodedata.normalize('NFC', request.POST['title'])
            link = unicodedata.normalize('NFC', request.POST['link'])

            # We separate each tag and create a list out of it.
            tags = unicodedata.normalize('NFC', request.POST['tags']).split(',')

            activated_bool = str2bool(unicodedata.normalize('NFC', request.POST['activated']))

            twitter_bool = str2bool(unicodedata.normalize('NFC', request.POST['twitter']))
            facebook_bool = str2bool(unicodedata.normalize('NFC', request.POST['facebook']))
            linkedin_bool = str2bool(unicodedata.normalize('NFC', request.POST['linkedin']))
            slack_bool = str2bool(unicodedata.normalize('NFC', request.POST['slack']))

            if str2bool(unicodedata.normalize('NFC', request.POST['autoformat'])):
                title = format_title(title)

            if title == "" or link == "":
                raise Exception("Title and/or Link is/are missing")

            tmp_post = Post.objects.create(title=title, link=link, clicks=0, user=user, activeLink=activated_bool)

            for i, tag in enumerate(tags):

                tag = tag.replace(" ", "")
                tags[i] = tag

                if tag != "":
                    tmp_obj, created_bool = Tag.objects.get_or_create(name=tag)
                    tmp_post.tags.add(tmp_obj)

                else:
                    tags.pop(i)

            tmp_post.save()

            if RSSArticle_Assoc_id != -1:
                RSSArticle_Assoc_obj.reposted = True
                RSSArticle_Assoc_obj.marked_read = True
                RSSArticle_Assoc_obj.save()

            if twitter_bool and user.is_social_network_enabled(network="twitter"):
                tasks.publish_on_twitter.delay(id_article=tmp_post.id)

            if facebook_bool and user.is_social_network_enabled(network="facebook"):
                tasks.publish_on_facebook.delay(id_article=tmp_post.id)

            if linkedin_bool and user.is_social_network_enabled(network="linkedin"):
                tasks.publish_on_linkedin.delay(id_article=tmp_post.id)

            if slack_bool and user.is_social_network_enabled(network="slack"):
                tasks.publish_on_slack.delay(id_article=tmp_post.id)

            payload["success"] = True
            payload["post_id"] = str(tmp_post.id)

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "submit article"
        payload["timestamp"] = get_timestamp()
        return Response(payload)

    def put(self, request, post_id=None):

        payload = dict()

        try:
            check_passed = check_admin_api(request.user)

            post_id = int(post_id)

            if type(post_id) is not int or post_id < 1:
                raise Exception("post_id parameter is not valid")

            if not check_passed:
                raise Exception(check_passed)

            payload["username"] = request.user.username

            title = unicodedata.normalize('NFC', request.data['title'])
            link = unicodedata.normalize('NFC', request.data['link'])

            if title == "" or link == "":
                raise Exception("Title and/or Link is/are missing")

            tags = unicodedata.normalize('NFC', request.data['tags']).split(
                ',')  # We separate each tag and create a list out of it.

            activated_bool = str2bool(unicodedata.normalize('NFC', request.data['activated']))

            twitter_bool = str2bool(unicodedata.normalize('NFC', request.POST['twitter']))
            facebook_bool = str2bool(unicodedata.normalize('NFC', request.POST['facebook']))
            linkedin_bool = str2bool(unicodedata.normalize('NFC', request.POST['linkedin']))
            slack_bool = str2bool(unicodedata.normalize('NFC', request.POST['slack']))

            if str2bool(unicodedata.normalize('NFC', request.data['autoformat'])):
                title = format_title(title)

            tmp_post = Post.objects.get(id=post_id, user=request.user)

            tmp_post.title = title
            tmp_post.link = link
            tmp_post.activeLink = activated_bool
            tmp_post.tags.clear()

            for i, tag in enumerate(tags):

                tag = tag.replace(" ", "")
                tags[i] = tag

                if tag != "":
                    tmp_obj, created_bool = Tag.objects.get_or_create(name=tag)
                    tmp_post.tags.add(tmp_obj)

                else:
                    tags.pop(i)

            tmp_post.save()

            if twitter_bool and request.user.is_social_network_enabled(network="twitter"):
                tasks.publish_on_twitter.delay(id_article=tmp_post.id)

            if facebook_bool and request.user.is_social_network_enabled(network="facebook"):
                tasks.publish_on_facebook.delay(id_article=tmp_post.id)

            if linkedin_bool and request.user.is_social_network_enabled(network="linkedin"):
                tasks.publish_on_linkedin.delay(id_article=tmp_post.id)

            if slack_bool and request.user.is_social_network_enabled(network="slack"):
                tasks.publish_on_slack.delay(id_article=tmp_post.id)

            payload["success"] = True
            payload["post_id"] = str(post_id)

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["post_id"] = None

        payload["operation"] = "modify article"
        payload["timestamp"] = get_timestamp()
        return Response(payload)

    def delete(self, request, post_id=None):

        payload = dict()

        try:
            check_passed = check_admin_api(request.user)

            post_id = int(unicodedata.normalize('NFC', post_id))
            if type(post_id) is not int or post_id < 1:
                raise Exception("post_id parameter is not valid")

            if not check_passed:
                raise Exception(check_passed)

            payload["username"] = request.user.username

            post = Post.objects.filter(id=post_id, user=request.user)
            if post.count() == 0:
                raise Exception("Post does not exist")

            post.delete()
            payload["success"] = True
            payload["post_id"] = post_id

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["post_id"] = None

        payload["operation"] = "delete article"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class ModifySlackPreferencesView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):

        payload = dict()

        try:
            for team, channels in request.data.items():
                if channels != "":
                    # Need to test if all channels exists
                    print(
                        "Warning - ModifySlackPreferencesView:Test implementation missing to check if the channel exist")

                # get object
                slack_integration = request.user.rel_slack_integrations.filter(team_name=team)[0]
                slack_integration.channels = channels
                slack_integration.save()

            payload["username"] = request.user.username
            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            print(str(e))
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "modify slack preferences"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class ModifySocialNetworksView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):

        payload = dict()

        try:
            payload["username"] = request.user.username

            url_validator = URLValidator()

            social_networks = [
                'dribbble',
                'facebook',
                'flickr',
                'gplus',
                'instagram',
                'linkedin',
                'pinterest',
                'stumble',
                'twitter',
                'vimeo',
                'youtube',
                'docker',
                'git',
                'kaggle',
                'stackoverflow',
                'coursera',
                'googlescholar',
                'orcid',
                'researchgate',
                'mendeley',
                'blog',
                'website'
            ]

            social_data = dict()
            for social in social_networks:
                url = unicodedata.normalize('NFC', request.data[social])
                if url != '':
                    try:
                        url_validator(url)  # Raise a ValidationError if the URL is invalid.
                    except:
                        raise Exception("URL Not Valid: " + social)
                social_data[social] = url

            # Main Social Networks
            request.user.social_dribbble = social_data['dribbble']
            request.user.social_facebook = social_data['facebook']
            request.user.social_flickr = social_data['flickr']
            request.user.social_gplus = social_data['gplus']
            request.user.social_instagram = social_data['instagram']
            request.user.social_linkedin = social_data['linkedin']
            request.user.social_pinterest = social_data['pinterest']
            request.user.social_stumble = social_data['stumble']
            request.user.social_twitter = social_data['twitter']
            request.user.social_vimeo = social_data['vimeo']
            request.user.social_youtube = social_data['youtube']

            # Computer Science Networks
            request.user.social_docker = social_data['docker']
            request.user.social_git = social_data['git']
            request.user.social_kaggle = social_data['kaggle']
            request.user.social_stackoverflow = social_data['stackoverflow']

            # MooC Profiles
            request.user.social_coursera = social_data['coursera']

            # Research Social Networks
            request.user.social_google_scholar = social_data['googlescholar']
            request.user.social_orcid = social_data['orcid']
            request.user.social_researchgate = social_data['researchgate']
            request.user.social_mendeley = social_data['mendeley']

            # Personal Pages
            request.user.social_blog = social_data['blog']
            request.user.social_personalwebsite = social_data['website']

            request.user.save()
            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "modify social networks"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class UserPreferencesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        payload = dict()

        try:
            payload["preferences"] = dict()

            payload["preferences"]["visibility"] = request.user.pref_post_public_visibility
            payload["preferences"]["autoformat"] = request.user.pref_post_autoformat

            if request.user.is_twitter_enabled():
                payload["preferences"]["twitter"] = request.user.pref_post_repost_TW
            else:
                payload["preferences"]["twitter"] = "disabled"

            if request.user.is_facebook_enabled():
                payload["preferences"]["facebook"] = request.user.pref_post_repost_FB
            else:
                payload["preferences"]["facebook"] = "disabled"

            if request.user.is_linkedin_enabled():
                payload["preferences"]["linkedin"] = request.user.pref_post_repost_LKin
            else:
                payload["preferences"]["linkedin"] = "disabled"

            if request.user.is_slack_enabled():
                payload["preferences"]["slack"] = request.user.pref_post_repost_Slack
            else:
                payload["preferences"]["slack"] = "disabled"

            payload["success"] = True

        except Exception as e:
            payload["error"] = "UserPreferencesView - GET: " + str(e)
            payload["success"] = False

        payload["operation"] = "Get personal preferences"
        payload["timestamp"] = get_timestamp()

        return Response(payload)

    def put(self, request):

        payload = dict()

        try:
            payload["username"] = request.user.username

            fields = [
                'visibility',
                'autoformat',
                'twitter',
                'facebook',
                'linkedin',
                'slack'
            ]

            form_data = dict()
            for field in fields:
                form_data[field] = str2bool(unicodedata.normalize('NFC', request.data[field]))

            request.user.pref_post_public_visibility = form_data["visibility"]
            request.user.pref_post_autoformat = form_data["autoformat"]

            request.user.pref_post_repost_TW = form_data["twitter"]
            request.user.pref_post_repost_FB = form_data["facebook"]
            request.user.pref_post_repost_LKin = form_data["linkedin"]
            request.user.pref_post_repost_Slack = form_data["slack"]

            request.user.save()
            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)

        payload["operation"] = "modify personal Information"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class ModifyPersonalInformationView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):

        payload = dict()

        try:
            payload["username"] = request.user.username

            url_validator = URLValidator()

            fields = [
                'firstname',
                'lastname',
                'email',
                'birthdate',
                'country',
                'gender',
                'feedtitle',  # not Checked
                'description',  # not Checked
                'job',  # not Checked
                'company_name',  # not Checked
                'company_website',
                "newsletter_subscription",  # Not Saved yet !
            ]

            form_data = dict()
            for field in fields:
                form_data[field] = unicodedata.normalize('NFC', request.data[field])

            ###############################################################################
            #                               DATA VALIDATION                               #
            ###############################################################################

            if form_data["firstname"] != "":
                FeedUser.objects._validate_firstname(form_data["firstname"])

            if form_data["lastname"] != "":
                FeedUser.objects._validate_lastname(form_data["lastname"])

            if form_data["gender"] != "":
                FeedUser.objects._validate_gender(form_data["gender"])

            FeedUser.objects._validate_email(form_data["email"])
            url_validator(form_data["company_website"])

            ###############################################################################
            #               DATA VALIDATION & Set Attributes - Special Attr               #
            ###############################################################################

            if form_data["birthdate"] != "":
                FeedUser.objects._validate_birthdate(form_data["birthdate"])
                request.user.birthdate = datetime.datetime.strptime(form_data["birthdate"], '%d/%m/%Y').date()
            else:
                request.user.birthdate = None

            if form_data["country"] != "":
                FeedUser.objects._validate_country(form_data["country"])
                request.user.country = Country.objects.get(name=form_data["country"])
            else:
                request.user.country = None

            ###############################################################################
            #                              SAVING ATTRIBUTES                              #
            ###############################################################################

            request.user.first_name = form_data["firstname"]
            request.user.last_name = form_data["lastname"]
            request.user.gender = form_data["gender"]
            request.user.email = form_data["email"]
            request.user.rss_feed_title = form_data["feedtitle"]
            request.user.description = form_data["description"]
            request.user.job = form_data["job"]
            request.user.company_name = form_data["company_name"]
            request.user.company_website = form_data["company_website"]
            request.user.pref_newsletter_subscription = str2bool(form_data["newsletter_subscription"])

            request.user.save()

            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["post_id"] = None

        payload["operation"] = "modify personal Information"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class ModifyPasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):

        payload = dict()

        try:
            payload["username"] = request.user.username

            form_fields = [
                'old_password',
                'new_password_1',
                'new_password_2',
            ]

            form_data = dict()

            for field in form_fields:
                form_data[field] = unicodedata.normalize('NFC', request.data[field])

            if (not request.user.check_password(form_data['old_password'])):
                raise Exception("Old Password is incorrect")

            if (form_data['new_password_1'] != form_data['new_password_2']):
                raise Exception("Your have input two different passwords, please retry.")

            request.user.set_password(form_data['new_password_1'])

            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["post_id"] = None

        payload["operation"] = "modify password"
        payload["timestamp"] = get_timestamp()
        return Response(payload)


class RSSArticleAssocView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, RSSArticle_AssocID=None):

        payload = dict()

        try:
            payload["username"] = request.user.username

            if RSSArticle_AssocID is not None:
                mark_RSSArticle_Assoc_as_read(RSSArticle_AssocID, request.user)

                payload["operation"] = "Mark RSSArticle_Assoc as Read"

            elif 'listing' in request.data:
                RSSArticle_Assoc_listing = unicodedata.normalize('NFC', request.POST['listing']).split(
                    ',')  # We separate each tag and create a list out of it.
                RSSArticle_Assoc_listing.pop()  # We remove the last element which is empty

                for article in RSSArticle_Assoc_listing:
                    mark_RSSArticle_Assoc_as_read(article, request.user)

                payload["operation"] = "Mark RSSArticles Listing as Read"

            else:
                raise Exception("Some Parameters are missing (rssArticleID or listing)")

            payload["success"] = True
            payload["RSSArticle_AssocID"] = RSSArticle_AssocID

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["rssArticleID"] = None

        payload["timestamp"] = get_timestamp()
        return Response(payload)


'''
class Modify_Photo(APIView):
    parser_classes = (FileUploadParser,)

    def put(self, request, filename=""):
        try:
            payload = dict()
            check_passed = check_admin_api(request.user)

            if check_passed != True:
                raise Exception(check_passed)
            payload ["username"] = request.user.username

            #unicodedata.normalize('NFC', request.data["photo"])
            photo = request.data['photo']

            allowed_mime_types = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png']

            if photo.content_type not in allowed_mime_types:
                raise ValueError("Only Images are allowed.")

            w, h = get_image_dimensions(photo.read())

            if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0 :

                if photo.size > 1000000: # > 1MB
                    raise ValueError("File size is larger than 1MB.")

                request.user = FeedUser.objects.get(username=request.user.username)
                request.user.profile_picture = photo
                request.user.save()
            else:
                raise ValueError("The uploaded image is not valid")

            payload["success"] = True

        except Exception as e:
            payload["success"] = False
            payload["error"] = "An error occured in the process: " + str(e)
            payload["post_id"] = None

        payload ["operation"] = "modify profile picture"
        payload ["timestamp"] = get_timestamp()
        return Response(payload)
'''
