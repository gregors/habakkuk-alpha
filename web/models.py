from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import Max
import json
import logging
logger = logging.getLogger(__name__)

class ClusterData(models.Model):
    # Clusters generated by machine learning app (ie mahout)
    date = models.DateField()
    range = models.PositiveIntegerField()
    created_at = models.DateTimeField()
    ml_json = models.TextField()
    # set in pre-save
    d3_dendogram_json = models.TextField()
    num_clusters = models.PositiveIntegerField()

    def __unicode__(self):
        return "<date(%s) range(%s) numclusters(%s)>"%(self.date, self.range, self.num_clusters)

    class Meta:
        unique_together = ('date', 'range')

def make_d3_data(sender, instance, *args, **kwargs):
    if instance.d3_dendogram_json:
        return

    d3_data = {"name":"%s, %d day range"%(instance.date, instance.range)}
    d3_data['children'] = []
    clusters = json.loads(instance.ml_json)
    facets = {}

    # child for every cluster
    for cluster in clusters:
        if not len(cluster.get('top_terms')):
            logger.error("found an empty cluster")
            continue

        d3_cluster = {}
        d3_cluster["size"] = 2 # users and bibleverses
        d3_cluster["name"] = cluster["top_terms"][0]["term"]
        
        topics = {"size":1,
                  "name":"'%s' topics"%d3_cluster["name"],
                  "children":[{"name":t['term'], "children":[]} for t in cluster["hk_topics"]]}

        # child for "bibleverses"
        num = len(cluster["top_terms"])
        bibleverses = {"size":num,
                       "name":"bibleverses (%s)"%num,
                       "children":[{"name":t['term'], "children":[]} for t in cluster["top_terms"]]}
                  
        d3_cluster["children"] = [topics, bibleverses]
        d3_data["children"].append(d3_cluster)

        for t in cluster["top_terms"]:
            t = t['term']
            facets[t] = facets.get(t,0)
            facets[t]+=1
    facets = [{'term':key, 'count':facets[key]} for key in facets]
    d3_data['facets'] = sorted(facets, key=lambda x: x.values()[0], reverse=True)
    instance.d3_dendogram_json = json.dumps(d3_data, indent=2)
    instance.num_clusters = len(d3_data["children"])

# TODO: Does this fire on update?
pre_save.connect(make_d3_data, sender=ClusterData)
